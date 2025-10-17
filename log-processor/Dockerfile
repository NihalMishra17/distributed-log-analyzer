FROM apache/spark:3.5.0-python3

USER root

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_processor.py .

CMD ["python3", "log_processor.py"]