from pathlib import Path
import os
import gradio as gr
import pandas as pd
from html import escape
from pipeline import run_pipeline, load_results, load_summary, detect_columns

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "kaggle_social"
OUTPUT_DIR = BASE / "output"


def _text_bars(summary, column, title, limit=8):
    """Render a small chart as plain Markdown, avoiding browser chart plugins."""
    if summary is None or summary.empty or column not in summary.columns:
        return f"### {title}\n\n_No data yet. Upload a CSV and run the analysis._"
    counts = (summary.groupby(column, dropna=False)["posts"].sum()
              .sort_values(ascending=False).head(limit))
    if counts.empty:
        return f"### {title}\n\n_No data to display._"
    maximum = max(int(counts.max()), 1)
    rows = [f"### {title}", ""]
    for label, count in counts.items():
        label = "Unknown" if pd.isna(label) else str(label)
        bar = "█" * max(1, round(24 * int(count) / maximum))
        rows.append(f"**{escape(label)}**  {bar} {int(count):,}")
    return "\n\n".join(rows)


def _csv_header(path):
    """Read the uploaded CSV header and map its text and label fields."""
    try:
        columns = [str(column) for column in pd.read_csv(path, nrows=0).columns]
    except Exception as exc:
        return [], None, None, str(exc)
    text_column, label_column = detect_columns(columns)
    return columns, text_column, label_column, None


def _dashboard_feedback(message, upload_value=None):
    """Show a recoverable status in the page without triggering a Gradio error overlay."""
    empty = pd.DataFrame(columns=["platform", "sentiment", "topic", "text"])
    waiting = "### Waiting for data\n\nUpload a CSV below, then run the analysis."
    outputs = (0, 0, "0%", waiting, waiting, waiting, empty, message)
    return outputs if READ_ONLY else (*outputs, upload_value)


def analyze(uploaded_file=None, run_dataset_if_needed=True):
    """Analyze an uploaded CSV, saved Kaggle files, or cached results."""
    status = ""
    if uploaded_file:
        columns, text_column, label_column, header_error = _csv_header(uploaded_file)
        if header_error or not text_column or not label_column:
            found = ", ".join(escape(name) for name in columns) if columns else "(could not read the CSV header)"
            message = ("CSV not analyzed. Include a post-text field such as text, tweet_text, post_text, comment, message, or content, "
                       "and a label field such as sentiment, category, label, emotion, or polarity. "
                       f"Columns found: {found}.")
            return _dashboard_feedback(message, uploaded_file)
        incoming = Path(uploaded_file)
        try:
            summary = run_pipeline(input_files=[incoming])
        except Exception as exc:
            return _dashboard_feedback(f"Analysis could not complete: {type(exc).__name__}: {exc}", uploaded_file)
        status = f"Analyzed uploaded file: {incoming.name}"

    cached_posts = list((OUTPUT_DIR / "spark_posts").glob("part-*.csv"))
    if not uploaded_file:
        source_files = list(DATA_DIR.glob("*.csv"))
        if cached_posts:
            summary = load_summary()
            status = "Loaded the saved Spark analysis."
        elif not run_dataset_if_needed:
            return _dashboard_feedback("No saved analysis yet. Upload a supported CSV and click Run PySpark analysis.")
        elif source_files:
            try:
                summary = run_pipeline()
            except Exception as exc:
                return _dashboard_feedback(f"Analysis could not complete: {type(exc).__name__}: {exc}")
            status = f"Analyzed {len(source_files)} CSV file(s) from the dataset folder."
        else:
            return _dashboard_feedback("No dataset loaded yet. Upload a CSV and run PySpark analysis, or download the Kaggle dataset first.")

    frame = load_results()
    if frame.empty:
        return _dashboard_feedback("No posts were found. Check that the CSV text and label fields contain data.", uploaded_file)
    platform_chart = _text_bars(summary, "platform", "Platform mix")
    sentiment_chart = _text_bars(summary, "sentiment", "Sentiment distribution")
    topic_chart = _text_bars(summary, "topic", "Topics (keyword-derived)")
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
        platform_plot = gr.Markdown("### Platform mix\n\nWaiting for data.")
        sentiment_plot = gr.Markdown("### Sentiment distribution\n\nWaiting for data.")
    topic_plot = gr.Markdown("### Topics (keyword-derived)\n\nWaiting for data.")
    posts = gr.Dataframe(label="Sample analyzed posts", interactive=False, wrap=True)
    status = gr.Markdown("Upload a supported CSV to begin, or download the Kaggle dataset.")
    analysis_outputs = [total, platforms, positive, platform_plot, sentiment_plot, topic_plot, posts, status]
    if READ_ONLY:
        gr.Markdown("Read-only public demo")
        refresh = gr.Button("Refresh dashboard", variant="primary")
        refresh.click(analyze, inputs=[], outputs=analysis_outputs)
        demo.load(lambda: analyze(run_dataset_if_needed=False), inputs=[], outputs=analysis_outputs)
    else:
        gr.Markdown("**Use your own data:** upload a CSV with a post-text column (for example text, tweet_text, post_text, comment, message, or content) and a label column (for example sentiment, category, label, or emotion), then click **Run PySpark analysis**.")
        upload = gr.File(label="Upload a social-media CSV", file_types=[".csv"], type="filepath")
        with gr.Row():
            run = gr.Button("Run PySpark analysis", variant="primary")
            fetch = gr.Button("Download Kaggle dataset")
        log = gr.Textbox(label="Download status", lines=3)
        run.click(analyze, inputs=[upload], outputs=analysis_outputs + [upload])
        fetch.click(download_kaggle, outputs=log)
        demo.load(lambda: analyze(run_dataset_if_needed=False), inputs=[], outputs=analysis_outputs + [upload])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=7860, show_error=True, share=os.getenv("GRADIO_SHARE", "false").lower() == "true", theme=gr.themes.Soft())
