FROM bitnami/spark:3.5

USER root

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_processor.py .

CMD ["python", "log_processor.py"]