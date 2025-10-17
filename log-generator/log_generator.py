import json
import random
import time
from datetime import datetime
from kafka import KafkaProducer
import os

class LogGenerator:
    def __init__(self, bootstrap_servers, log_rate=1000):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.log_rate = log_rate
        
        # Service types
        self.services = ['web-api', 'auth-service', 'payment-service', 'database', 'cache-service']
        
        # Log levels with weighted probabilities
        self.log_levels = ['INFO', 'WARN', 'ERROR', 'DEBUG', 'CRITICAL']
        self.level_weights = [0.70, 0.15, 0.10, 0.04, 0.01]  # 70% INFO, 10% ERROR, etc.
        
        # Common log messages
        self.messages = {
            'INFO': [
                'Request processed successfully',
                'User logged in',
                'Data fetched from cache',
                'API call completed',
                'Transaction committed'
            ],
            'WARN': [
                'Slow query detected',
                'High memory usage',
                'Cache miss',
                'Rate limit approaching',
                'Deprecated API used'
            ],
            'ERROR': [
                'Database connection failed',
                'Authentication failed',
                'Timeout occurred',
                'Invalid request format',
                'Service unavailable'
            ],
            'DEBUG': [
                'Function entry',
                'Variable state',
                'Processing step completed',
                'Cache hit'
            ],
            'CRITICAL': [
                'System crash',
                'Data corruption detected',
                'Security breach attempt',
                'Service completely down'
            ]
        }
        
        # Response time ranges (in ms)
        self.response_times = {
            'INFO': (10, 200),
            'WARN': (200, 500),
            'ERROR': (500, 2000),
            'DEBUG': (5, 50),
            'CRITICAL': (1000, 5000)
        }

    def generate_log(self):
        """Generate a realistic log entry"""
        service = random.choice(self.services)
        level = random.choices(self.log_levels, weights=self.level_weights)[0]
        message = random.choice(self.messages[level])
        
        # Generate response time based on log level
        min_time, max_time = self.response_times[level]
        response_time = random.randint(min_time, max_time)
        
        # Add anomaly patterns (for testing detection)
        is_anomaly = False
        if random.random() < 0.05:  # 5% anomalies
            is_anomaly = True
            if level == 'ERROR':
                response_time *= 3  # Errors take longer
            if service == 'database':
                response_time *= 2  # Database issues
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': service,
            'level': level,
            'message': message,
            'response_time_ms': response_time,
            'user_id': f"user_{random.randint(1000, 9999)}",
            'request_id': f"req_{random.randint(100000, 999999)}",
            'ip_address': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'endpoint': f"/api/v1/{random.choice(['users', 'products', 'orders', 'payments'])}",
            'is_anomaly': is_anomaly  # Ground truth for testing
        }
        
        return log_entry

    def run(self):
        """Start generating logs"""
        print(f"Starting log generator - Target rate: {self.log_rate} logs/second")
        print(f"Sending logs to Kafka topic: 'logs'")
        
        logs_sent = 0
        start_time = time.time()
        
        try:
            while True:
                log = self.generate_log()
                self.producer.send('logs', value=log)
                logs_sent += 1
                
                # Report stats every 10 seconds
                if logs_sent % (self.log_rate * 10) == 0:
                    elapsed = time.time() - start_time
                    actual_rate = logs_sent / elapsed
                    print(f"Logs sent: {logs_sent:,} | Rate: {actual_rate:.0f} logs/sec")
                
                # Control rate
                time.sleep(1.0 / self.log_rate)
                
        except KeyboardInterrupt:
            print("\nStopping log generator...")
            elapsed = time.time() - start_time
            print(f"Total logs sent: {logs_sent:,}")
            print(f"Average rate: {logs_sent / elapsed:.0f} logs/sec")
        finally:
            self.producer.close()

if __name__ == "__main__":
    kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    log_rate = int(os.getenv('LOG_RATE', '1000'))
    
    # Wait for Kafka to be ready
    print("Waiting for Kafka to be ready...")
    time.sleep(10)
    
    generator = LogGenerator(kafka_servers, log_rate)
    generator.run()