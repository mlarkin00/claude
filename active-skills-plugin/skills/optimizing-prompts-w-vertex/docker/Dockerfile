FROM python:3.12-slim

RUN pip install --no-cache-dir "google-cloud-aiplatform>=1.87.0"

WORKDIR /skill
COPY optimize_prompt.py .

ENTRYPOINT ["python", "optimize_prompt.py"]
