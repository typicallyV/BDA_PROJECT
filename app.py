from pathlib import Path
import os
import gradio as gr
import pandas as pd
import re
import plotly.express as px
from pipeline import run_pipeline, load_results, load_summary

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "kaggle_social"
OUTPUT_DIR = BASE / "output"


def _is_supported_csv(path):
    """Check only the header before accepting a social-media CSV upload."""
    try:
        columns = {re.sub(r"[^a-z0-9]+", "", str(c).lower()) for c in pd.read_csv(path, nrows=0).columns}
    except Exception:
        return False
    text_names = {"cleantext", "cleancomment", "text", "comment", "tweet", "content", "post"}
    label_names = {"category", "sentiment", "label", "polarity"}
    return bool(columns & text_names) and bool(columns & label_names)


def analyze(uploaded_file=None):
    """Analyze one uploaded CSV, saved Kaggle files, or cached results."""
    status = ""
    if uploaded_file:
        if not _is_supported_csv(uploaded_file):
            raise gr.Error("This CSV needs a post-text column (for example text or clean_text) and a sentiment column (for example category or sentiment).")
        incoming = Path(uploaded_file)
        summary = run_pipeline(input_files=[incoming])
        status = f"Analyzed uploaded file: {incoming.name}"

    cached_posts = list((OUTPUT_DIR / "spark_posts").glob("part-*.csv"))
    if not uploaded_file:
        source_files = list(DATA_DIR.glob("*.csv"))
        if cached_posts:
            summary = load_summary()
            status = "Loaded the saved Spark analysis."
        elif source_files:
            summary = run_pipeline()
            status = f"Analyzed {len(source_files)} CSV file(s) from the dataset folder."
        else:
            empty = pd.DataFrame(columns=["platform", "sentiment", "topic", "text"])
            outputs = (0, 0, "0%", None, None, None, empty,
                       "No dataset loaded yet. Upload a CSV below and click Run PySpark analysis, or download the Kaggle dataset first.")
            return outputs if READ_ONLY else (*outputs, None)

    frame = load_results()
    if frame.empty:
        raise gr.Error("No posts were found in that CSV. Check that its text and sentiment columns contain data.")
    platform_chart = px.bar(summary.groupby("platform", as_index=False)["posts"].sum(), x="platform", y="posts", color="platform", title="Posts by platform")
    sentiment_chart = px.bar(summary.groupby("sentiment", as_index=False)["posts"].sum(), x="sentiment", y="posts", color="sentiment", title="Sentiment distribution")
    topic_chart = px.bar(summary.groupby("topic", as_index=False)["posts"].sum(), x="topic", y="posts", color="topic", title="Most discussed topics")
    top = frame[["platform", "sentiment", "topic", "text"]].head(100)
    outputs = (
        len(frame), frame["platform"].nunique(),
        f"{(frame['sentiment'] == 'Positive').mean() * 100:.1f}%",
        platform_chart, sentiment_chart, topic_chart, top,
        f"{status}. Processed {len(frame):,} post(s)."
    )
    return outputs if READ_ONLY else (*outputs, None)
def download_kaggle():
    import subprocess, sys
    result = subprocess.run([sys.executable, str(BASE / "download_dataset.py")], cwd=str(BASE), capture_output=True, text=True)
    if result.returncode:
        raise gr.Error((result.stderr or result.stdout)[-1500:])
    return result.stdout[-2000:]

READ_ONLY = os.getenv("GRADIO_READONLY", "false").lower() == "true"
with gr.Blocks(title="Social Media Analytics | Spark + Hadoop + Cassandra") as demo:
    gr.Markdown("# Social Media Analytics\n**Twitter + Reddit sentiment** · PySpark processing · Hadoop-compatible storage · Cassandra archive")
    gr.Markdown("Dataset: [Twitter and Reddit Sentimental Analysis](https://www.kaggle.com/datasets/cosmos98/twitter-and-reddit-sentimental-analysis-dataset) — roughly 200K labeled public posts/comments.")
    with gr.Row():
        total = gr.Number(label="Records", precision=0)
        platforms = gr.Number(label="Platforms", precision=0)
        positive = gr.Textbox(label="Positive posts")
    with gr.Row():
        platform_plot = gr.Plot(label="Platform mix")
        sentiment_plot = gr.Plot(label="Sentiment")
    topic_plot = gr.Plot(label="Topics (keyword-derived)")
    posts = gr.Dataframe(label="Sample analyzed posts", interactive=False, wrap=True)
    status = gr.Markdown("Upload a supported CSV to begin, or download the Kaggle dataset.")
    analysis_outputs = [total, platforms, positive, platform_plot, sentiment_plot, topic_plot, posts, status]
    if READ_ONLY:
        gr.Markdown("Read-only public demo")
        refresh = gr.Button("Refresh dashboard", variant="primary")
        refresh.click(analyze, inputs=[], outputs=analysis_outputs)
        demo.load(analyze, inputs=[], outputs=analysis_outputs)
    else:
        gr.Markdown("**Use your own data:** upload a CSV with a post-text column (text, clean_text, comment, etc.) and a sentiment/label column (sentiment, category, label, etc.), then click **Run PySpark analysis**.")
        upload = gr.File(label="Upload a social-media CSV", file_types=[".csv"], type="filepath")
        with gr.Row():
            run = gr.Button("Run PySpark analysis", variant="primary")
            fetch = gr.Button("Download Kaggle dataset")
        log = gr.Textbox(label="Download status", lines=3)
        run.click(analyze, inputs=[upload], outputs=analysis_outputs + [upload])
        fetch.click(download_kaggle, outputs=log)
        demo.load(analyze, inputs=[], outputs=analysis_outputs + [upload])
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True, share=os.getenv("GRADIO_SHARE", "false").lower() == "true", theme=gr.themes.Soft())










