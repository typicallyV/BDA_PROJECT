from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from io import BytesIO

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data" / "kaggle_social"
DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/cosmos98/twitter-and-reddit-sentimental-analysis-dataset"
EXPECTED = {"Reddit_Data.csv", "Twitter_Data.csv"}


def download_archive():
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "social-media-analytics/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def extract_csvs(archive_bytes):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    extracted = set()
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        for member in archive.infolist():
            name = Path(member.filename).name
            if name in EXPECTED and not member.is_dir():
                destination = DATA_DIR / name
                with archive.open(member) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                extracted.add(name)
    missing = EXPECTED - extracted
    if missing:
        raise ValueError("Kaggle archive did not contain: " + ", ".join(sorted(missing)))


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if all((DATA_DIR / name).exists() for name in EXPECTED):
        print("Kaggle dataset already present:", DATA_DIR)
        return 0
    try:
        archive = download_archive()
        extract_csvs(archive)
        print("Downloaded and extracted Twitter_Data.csv and Reddit_Data.csv to", DATA_DIR)
        return 0
    except Exception as error:
        print("Direct Kaggle download failed:", error, file=sys.stderr)
        print("Trying the Kaggle CLI (requires API credentials)...", file=sys.stderr)
        result = subprocess.run([
            sys.executable, "-m", "kaggle", "datasets", "download",
            "-d", "cosmos98/twitter-and-reddit-sentimental-analysis-dataset",
            "-p", str(DATA_DIR), "--unzip"
        ], cwd=str(BASE))
        if result.returncode == 0 and all((DATA_DIR / name).exists() for name in EXPECTED):
            return 0
        print("Download the files manually from https://www.kaggle.com/datasets/cosmos98/twitter-and-reddit-sentimental-analysis-dataset", file=sys.stderr)
        return result.returncode or 1


if __name__ == "__main__":
    raise SystemExit(main())
