# Social Media Analytics

A Gradio dashboard built with PySpark for the Kaggle [Twitter and Reddit Sentimental Analysis dataset](https://www.kaggle.com/datasets/cosmos98/twitter-and-reddit-sentimental-analysis-dataset). The app analyzes roughly 200K labeled public posts and comments.

## Run locally on Windows

1. Install Python 3.10–3.12, Java 8/11/17, Docker Desktop, and Hadoop if you want the Streaming job.
2. Run `SETUP_CASSANDRA.cmd` to start Cassandra.
3. Run `START_HADOOP.cmd` to start the workspace-local single-node HDFS (optional).
4. Run `START_PROJECT.cmd`. It installs Python packages, downloads the public Kaggle CSVs, and starts Gradio on http://127.0.0.1:7860.
5. Click **Run PySpark analysis**. Use `RUN_HADOOP.cmd` to count posts by platform in HDFS.

To create a temporary public Gradio share while the local process is running, use `START_GRADIO_PUBLIC.cmd`. The share ends when the local process stops.

## Host it with Docker

The included `Dockerfile` builds a Gradio + PySpark app image with Java 17. Build and run it:

```bash
docker build -t social-media-analytics .
docker run --rm -p 7860:7860 social-media-analytics
```

Open http://localhost:7860, choose **Download Kaggle dataset**, then **Run PySpark analysis**. The downloader first fetches the public Kaggle archive directly; it falls back to Kaggle CLI credentials if Kaggle blocks the direct request.

The Docker image runs the Gradio app and local Spark. Cassandra and HDFS are separate optional services; set `CASSANDRA_HOST`/`CASSANDRA_PORT` and `HDFS_URI` only when those services are reachable from the container. The Windows `START_HADOOP.cmd` setup is for local development and is not used by the hosted Docker image.

## Deploy to Hugging Face Spaces

This repository includes Docker Space metadata in this README. Create a Docker Space and connect/push this repository to it. Spaces supports Docker-based apps and exposes port 7860. The Space can run the dashboard and local Spark; persistent Cassandra/HDFS requires separately hosted endpoints and secrets. See the [Hugging Face Spaces documentation](https://huggingface.co/docs/hub/spaces) and [Docker Spaces setup](https://huggingface.co/docs/hub/spaces-sdks-docker).

## Data and analysis notes

- The Kaggle dataset is licensed CC BY-NC-SA 4.0; review its terms before redistributing the source files.
- Dataset CSVs, Spark output, Hadoop data, and local dependency folders are excluded from Git.
- Sentiment labels are normalized from the dataset. Topic labels are assigned with transparent keyword rules, not a trained model.
- Processed Spark CSV files are written to `output/spark_posts/`; summaries to `output/spark_summary/`. When configured, HDFS receives Parquet output under `/social-media/` and Cassandra receives rows in `social_media_db.social_posts`.
