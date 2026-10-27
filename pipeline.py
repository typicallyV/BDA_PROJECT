from pathlib import Path
import os
import re
import sys
from pyspark.sql import SparkSession, functions as F, types as T

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "kaggle_social"
OUTPUT_DIR = BASE / "output"

TEXT_NAMES = ("clean_text", "clean_comment", "text", "comment", "tweet", "content", "post")
LABEL_NAMES = ("category", "sentiment", "label", "polarity")
TOPICS = {
    "Politics": ("government", "election", "minister", "modi", "politic", "vote", "leader"),
    "Technology": ("technology", "tech", "phone", "app", "internet", "software", "ai"),
    "Business": ("business", "company", "market", "money", "job", "price", "brand"),
    "Sports": ("sport", "cricket", "football", "team", "match", "player", "game"),
    "Entertainment": ("movie", "music", "film", "actor", "song", "show", "celebrity"),
    "Other": (),
}


def _normalized(name):
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _topic(text):
    text = (text or "").lower()
    for topic, words in TOPICS.items():
        if topic == "Other":
            continue
        if any(word in text for word in words):
            return topic
    return "Other"


def _sentiment(value):
    s = str(value).strip().lower()
    if s in ("-1", "-1.0", "negative", "neg", "negative sentiment"):
        return "Negative"
    if s in ("0", "0.0", "neutral", "neut", "neutral sentiment"):
        return "Neutral"
    if s in ("1", "1.0", "positive", "pos", "positive sentiment", "2", "2.0"):
        return "Positive"
    return s.title() or "Unknown"


def spark_session():
    # Keep Windows Spark workers on the same interpreter as this process.
    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
    builder = (SparkSession.builder.appName("SocialMediaSentimentAnalysis")
               .master(os.getenv("SPARK_MASTER", "local[*]"))
               .config("spark.pyspark.python", sys.executable)
               .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "8")))
    cassandra_host = os.getenv("CASSANDRA_HOST")
    if cassandra_host:
        builder = builder.config("spark.cassandra.connection.host", cassandra_host)
    return builder.getOrCreate()


def run_pipeline():
    """Normalize the two Kaggle CSVs, analyze with Spark, and persist outputs."""
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError("No Kaggle CSVs found under data/kaggle_social. Run download_dataset.py first.")
    spark = spark_session()
    try:
        normalized = []
        for path in files:
            raw = spark.read.option("header", True).option("inferSchema", True).option("multiLine", True).csv(path.resolve().as_uri())
            columns = {_normalized(c): c for c in raw.columns}
            text_col = next((columns[_normalized(n)] for n in TEXT_NAMES if _normalized(n) in columns), None)
            label_col = next((columns[_normalized(n)] for n in LABEL_NAMES if _normalized(n) in columns), None)
            if not text_col or not label_col:
                print("Skipping CSV without supported text and sentiment columns:", path.name)
                continue
            platform = "Reddit" if "reddit" in path.name.lower() else "Twitter" if "twitter" in path.name.lower() else path.stem.title()
            rows = raw.select(F.col(text_col).cast("string").alias("text"), F.col(label_col).cast("string").alias("raw_sentiment"))
            rows = rows.withColumn("platform", F.lit(platform))
            normalized.append(rows)
        if not normalized:
            raise ValueError("No CSV files with supported post-text and sentiment columns were found in " + str(DATA_DIR))
        data = normalized[0]
        for other in normalized[1:]:
            data = data.unionByName(other)
        # Keep normalization in Spark SQL expressions so Windows needs no Python UDF workers.
        raw_label = F.lower(F.trim(F.col("raw_sentiment")))
        text_lower = F.lower(F.col("text"))
        sentiment_expr = (F.when(raw_label.isin("-1", "-1.0", "negative", "neg"), "Negative")
                          .when(raw_label.isin("0", "0.0", "neutral", "neut"), "Neutral")
                          .when(raw_label.isin("1", "1.0", "2", "2.0", "positive", "pos"), "Positive")
                          .otherwise(F.initcap(raw_label)))
        topic_expr = (F.when(text_lower.rlike("government|election|minister|modi|politic|vote|leader"), "Politics")
                      .when(text_lower.rlike("technology|tech|phone|app|internet|software|\\bai\\b"), "Technology")
                      .when(text_lower.rlike("business|company|market|money|job|price|brand"), "Business")
                      .when(text_lower.rlike("sport|cricket|football|team|match|player|game"), "Sports")
                      .when(text_lower.rlike("movie|music|film|actor|song|show|celebrity"), "Entertainment")
                      .otherwise("Other"))
        data = (data.filter(F.col("text").isNotNull() & (F.length(F.trim("text")) > 0))
                .withColumn("sentiment", sentiment_expr)
                .withColumn("topic", topic_expr))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        data.write.mode("overwrite").option("header", True).csv((OUTPUT_DIR / "spark_posts").resolve().as_uri())
        summary = data.groupBy("platform", "sentiment", "topic").count().withColumnRenamed("count", "posts")
        summary.write.mode("overwrite").option("header", True).csv((OUTPUT_DIR / "spark_summary").resolve().as_uri())
        # Optional HDFS output: set HDFS_URI (e.g. hdfs://localhost:9000).
        hdfs_uri = os.getenv("HDFS_URI")
        if hdfs_uri:
            data.write.mode("overwrite").parquet(hdfs_uri.rstrip("/") + "/social-media/processed")
            summary.write.mode("overwrite").parquet(hdfs_uri.rstrip("/") + "/social-media/summary")
        # Cassandra is an optional archive. The driver is created by SETUP_CASSANDRA.cmd.
        if os.getenv("CASSANDRA_HOST"):
            from cassandra.cluster import Cluster
            from cassandra.query import BatchStatement, ConsistencyLevel
            cluster = Cluster([os.getenv("CASSANDRA_HOST", "127.0.0.1")], port=int(os.getenv("CASSANDRA_PORT", "9042")))
            try:
                session = cluster.connect("social_media_db")
                insert = session.prepare("INSERT INTO social_posts (post_id, platform, sentiment, topic, content) VALUES (?, ?, ?, ?, ?)")
                batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
                batch_count = 0
                for i, row in enumerate(data.select("platform", "sentiment", "topic", "text").toLocalIterator()):
                    post_id = str(i)
                    batch.add(insert, (post_id, row.platform, row.sentiment, row.topic, row.text[:4000]))
                    batch_count += 1
                    if batch_count >= 50:
                        session.execute(batch)
                        batch = BatchStatement(consistency_level=ConsistencyLevel.QUORUM)
                        batch_count = 0
                if batch_count:
                    session.execute(batch)
            finally:
                cluster.shutdown()
        return _read_spark_csv(OUTPUT_DIR / "spark_summary")
    finally:
        spark.stop()


def _read_spark_csv(path):
    parts = list(path.glob("part-*.csv"))
    import pandas as pd
    return pd.concat([pd.read_csv(p) for p in parts], ignore_index=True) if parts else pd.DataFrame(columns=["platform", "sentiment", "topic", "posts"])


def load_results():
    import pandas as pd
    path = OUTPUT_DIR / "spark_posts"
    parts = list(path.glob("part-*.csv"))
    return pd.concat([pd.read_csv(p) for p in parts], ignore_index=True) if parts else pd.DataFrame(columns=["text", "raw_sentiment", "platform", "sentiment", "topic"])








def load_summary():
    """Read the previously generated Spark summary without rerunning Spark."""
    return _read_spark_csv(OUTPUT_DIR / "spark_summary")


