FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY es_indexer.py .

CMD ["python", "es_indexer.py"]