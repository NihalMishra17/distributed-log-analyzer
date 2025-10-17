import os
import json
import redis
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, avg, max as spark_max
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, BooleanType
from datetime import datetime
import numpy as np
from collections import defaultdict

class AnomalyDetector:
    """ML-based anomaly detection using statistical methods"""
    
    def __init__(self):
        # Store historical metrics for baseline
        self.response_time_baseline = defaultdict(list)
        self.error_rate_baseline = defaultdict(list)
        self.threshold_multiplier = 3  # 3 standard deviations
        
    def detect_response_time_anomaly(self, service, response_time):
        """Detect if response time is anomalous"""
        baseline = self.response_time_baseline[service]
        
        if len(baseline) < 10:  # Need minimum data
            self.response_time_baseline[service].append(response_time)
            return False, 0
        
        # Keep sliding window of last 1000 values
        if len(baseline) > 1000:
            baseline = baseline[-1000:]
            self.response_time_baseline[service] = baseline
        
        mean = np.mean(baseline)
        std = np.std(baseline)
        
        # Z-score based detection
        if std > 0:
            z_score = (response_time - mean) / std
            is_anomaly = abs(z_score) > self.threshold_multiplier
            
            # Update baseline if not anomaly
            if not is_anomaly:
                self.response_time_baseline[service].append(response_time)
            
            return is_anomaly, z_score
        
        self.response_time_baseline[service].append(response_time)
        return False, 0
    
    def detect_error_spike(self, service, error_count, total_count):
        """Detect sudden spike in error rate"""
        if total_count == 0:
            return False, 0
        
        current_rate = error_count / total_count
        baseline = self.error_rate_baseline[service]
        
        if len(baseline) < 5:
            self.error_rate_baseline[service].append(current_rate)
            return False, 0
        
        mean_rate = np.mean(baseline[-100:])  # Last 100 windows
        
        # Detect spike (current rate is 5x baseline)
        is_spike = current_rate > (mean_rate * 5) and current_rate > 0.1
        
        self.error_rate_baseline[service].append(current_rate)
        
        return is_spike, current_rate

class LogProcessor:
    def __init__(self, kafka_bootstrap_servers, redis_host, redis_port, spark_master):
        # Initialize Spark Session
        self.spark = SparkSession.builder \
            .appName("DistributedLogAnalyzer") \
            .master(spark_master) \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        self.anomaly_detector = AnomalyDetector()
        
        # Define schema for log entries
        self.log_schema = StructType([
            StructField("timestamp", StringType(), True),
            StructField("service", StringType(), True),
            StructField("level", StringType(), True),
            StructField("message", StringType(), True),
            StructField("response_time_ms", IntegerType(), True),
            StructField("user_id", StringType(), True),
            StructField("request_id", StringType(), True),
            StructField("ip_address", StringType(), True),
            StructField("endpoint", StringType(), True),
            StructField("is_anomaly", BooleanType(), True)
        ])
    
    def process_batch(self, df, batch_id):
        """Process each micro-batch"""
        if df.isEmpty():
            return
        
        # Convert to pandas for easier processing
        pandas_df = df.toPandas()
        
        # Update metrics in Redis
        total_logs = len(pandas_df)
        error_logs = len(pandas_df[pandas_df['level'].isin(['ERROR', 'CRITICAL'])])
        
        # Store in Redis
        self.redis_client.hincrby('metrics', 'total_logs', total_logs)
        self.redis_client.hincrby('metrics', 'error_logs', error_logs)
        self.redis_client.hset('metrics', 'last_batch_time', datetime.utcnow().isoformat())
        
        # Service-level metrics
        for service in pandas_df['service'].unique():
            service_logs = pandas_df[pandas_df['service'] == service]
            service_errors = len(service_logs[service_logs['level'].isin(['ERROR', 'CRITICAL'])])
            avg_response = service_logs['response_time_ms'].mean()
            
            self.redis_client.hset(f'service:{service}', 'total_logs', len(service_logs))
            self.redis_client.hset(f'service:{service}', 'error_logs', service_errors)
            self.redis_client.hset(f'service:{service}', 'avg_response_time', f"{avg_response:.2f}")
            
            # Anomaly detection
            is_rt_anomaly, z_score = self.anomaly_detector.detect_response_time_anomaly(
                service, avg_response
            )
            is_error_spike, error_rate = self.anomaly_detector.detect_error_spike(
                service, service_errors, len(service_logs)
            )
            
            if is_rt_anomaly:
                anomaly = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': service,
                    'type': 'high_latency',
                    'value': f"{avg_response:.2f}ms",
                    'z_score': f"{z_score:.2f}"
                }
                self.redis_client.lpush('anomalies', json.dumps(anomaly))
                self.redis_client.ltrim('anomalies', 0, 99)  # Keep last 100
                self.redis_client.hincrby('metrics', 'anomalies_detected', 1)
            
            if is_error_spike:
                anomaly = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': service,
                    'type': 'error_spike',
                    'value': f"{error_rate*100:.1f}%",
                    'description': f"Error rate spiked to {error_rate*100:.1f}%"
                }
                self.redis_client.lpush('anomalies', json.dumps(anomaly))
                self.redis_client.ltrim('anomalies', 0, 99)
                self.redis_client.hincrby('metrics', 'anomalies_detected', 1)
        
        # Store recent logs
        for _, log in pandas_df.head(100).iterrows():
            self.redis_client.lpush('recent_logs', json.dumps(log.to_dict(), default=str))
        self.redis_client.ltrim('recent_logs', 0, 999)  # Keep last 1000
        
        print(f"Batch {batch_id}: Processed {total_logs} logs, {error_logs} errors")
    
    def run(self):
        """Start stream processing"""
        print("Starting Spark Streaming log processor...")
        print(f"Connecting to Kafka: {self.kafka_bootstrap_servers}")
        
        # Read from Kafka
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_bootstrap_servers) \
            .option("subscribe", "logs") \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON
        parsed_df = df.select(
            from_json(col("value").cast("string"), self.log_schema).alias("log")
        ).select("log.*")
        
        # Process in micro-batches
        query = parsed_df \
            .writeStream \
            .foreachBatch(self.process_batch) \
            .outputMode("append") \
            .trigger(processingTime='5 seconds') \
            .start()
        
        print("Stream processing started. Waiting for data...")
        query.awaitTermination()

if __name__ == "__main__":
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    spark_master = os.getenv('SPARK_MASTER', 'local[*]')
    
    import time
    print("Waiting for services to be ready...")
    time.sleep(30)  # Wait for Kafka and Spark
    
    processor = LogProcessor(kafka_servers, redis_host, redis_port, spark_master)
    processor.run()