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
    """Process social-media CSVs, or show the existing Kaggle analysis."""
    if uploaded_file:
        if _is_supported_csv(uploaded_file):
            import shutil
            incoming = Path(uploaded_file)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(incoming, DATA_DIR / incoming.name)
        else:
            gr.Warning("That CSV is not a social-media dataset. Showing the existing Kaggle analysis instead.")
            uploaded_file = None
    cached_posts = list((OUTPUT_DIR / "spark_posts").glob("part-*.csv"))
    summary = run_pipeline() if uploaded_file or not cached_posts else load_summary()
    frame = load_results()
    if frame.empty:
        raise gr.Error("No posts found. Keep the Kaggle CSVs in data/kaggle_social and rerun the analysis.")
    platform_chart = px.bar(summary.groupby("platform", as_index=False)["posts"].sum(), x="platform", y="posts", color="platform", title="Posts by platform")
    sentiment_chart = px.bar(summary.groupby("sentiment", as_index=False)["posts"].sum(), x="sentiment", y="posts", color="sentiment", title="Sentiment distribution")
    topic_chart = px.bar(summary.groupby("topic", as_index=False)["posts"].sum(), x="topic", y="posts", color="topic", title="Most discussed topics")
    top = frame[["platform", "sentiment", "topic", "text"]].head(100)
    outputs = (
        len(frame), frame["platform"].nunique(),
        f"{(frame['sentiment'] == 'Positive').mean() * 100:.1f}%",
        platform_chart, sentiment_chart, topic_chart, top
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
    analysis_outputs = [total, platforms, positive, platform_plot, sentiment_plot, topic_plot, posts]
    if READ_ONLY:
        gr.Markdown("Read-only public demo")
        refresh = gr.Button("Refresh dashboard", variant="primary")
        refresh.click(analyze, inputs=[], outputs=analysis_outputs)
        demo.load(analyze, inputs=[], outputs=analysis_outputs)
    else:
        upload = gr.File(label="Optional: add a CSV", file_types=[".csv"], type="filepath")
        with gr.Row():
            run = gr.Button("Run PySpark analysis", variant="primary")
            fetch = gr.Button("Download Kaggle dataset")
        log = gr.Textbox(label="Download status", lines=3)
        run.click(analyze, inputs=[upload], outputs=analysis_outputs + [upload])
        fetch.click(download_kaggle, outputs=log)
        demo.load(analyze, inputs=[], outputs=analysis_outputs + [upload])
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_error=True, share=os.getenv("GRADIO_SHARE", "false").lower() == "true", theme=gr.themes.Soft())










