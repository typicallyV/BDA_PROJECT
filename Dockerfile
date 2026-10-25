FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app.py pipeline.py download_dataset.py ./
COPY schema.cql README.md ./

RUN mkdir -p data/kaggle_social output
EXPOSE 7860
CMD ["python", "app.py"]
