FROM eclipse-temurin:17-jre AS java_runtime

FROM python:3.12-slim

ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY --from=java_runtime /opt/java/openjdk /opt/java/openjdk

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app.py pipeline.py download_dataset.py ./
COPY schema.cql README.md ./

RUN mkdir -p data/kaggle_social output
EXPOSE 7860
CMD ["python", "app.py"]
