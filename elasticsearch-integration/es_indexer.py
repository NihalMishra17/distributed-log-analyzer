from elasticsearch import Elasticsearch
from datetime import datetime
import json
import redis
import time
import os

class ElasticsearchIndexer:
    def __init__(self, es_host='elasticsearch', redis_host='redis'):
        # Connect to Elasticsearch
        self.es = Elasticsearch([f'http://{es_host}:9200'])
        
        # Connect to Redis
        self.redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)
        
        # Index name
        self.index_name = 'logs'
        
        # Wait for Elasticsearch to be ready
        self.wait_for_elasticsearch()
        
        # Create index with mapping
        self.create_index()
    
    def wait_for_elasticsearch(self):
        """Wait for Elasticsearch to be ready"""
        print("Waiting for Elasticsearch...", flush=True)
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if self.es.ping():
                    print("✓ Elasticsearch is ready!", flush=True)
                    return
            except:
                pass
            
            retry_count += 1
            time.sleep(2)
        
        raise Exception("Elasticsearch failed to start")
    
    def create_index(self):
        """Create index with proper mapping"""
        mapping = {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "service": {"type": "keyword"},
                    "level": {"type": "keyword"},
                    "message": {"type": "text"},
                    "response_time_ms": {"type": "integer"},
                    "user_id": {"type": "keyword"},
                    "request_id": {"type": "keyword"},
                    "ip_address": {"type": "ip"},
                    "endpoint": {"type": "keyword"},
                    "is_anomaly": {"type": "boolean"}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        
        # Create index if it doesn't exist
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=mapping)
            print(f"✓ Created index: {self.index_name}", flush=True)
        else:
            print(f"✓ Index {self.index_name} already exists", flush=True)
    
    def index_logs_from_redis(self):
        """Index recent logs from Redis into Elasticsearch"""
        # Get recent logs from Redis
        logs_raw = self.redis_client.lrange('recent_logs', 0, 999)
        
        if not logs_raw:
            print("No logs in Redis to index", flush=True)
            return 0
        
        # Prepare bulk indexing
        actions = []
        for log_str in logs_raw:
            try:
                log = json.loads(log_str)
                
                # Convert timestamp to Elasticsearch format
                if 'timestamp' in log:
                    try:
                        log['timestamp'] = datetime.fromisoformat(log['timestamp'])
                    except:
                        log['timestamp'] = datetime.utcnow()
                
                action = {
                    "index": {
                        "_index": self.index_name,
                        "_id": log.get('request_id', None)
                    }
                }
                actions.append(action)
                actions.append(log)
            except Exception as e:
                print(f"Error processing log: {e}", flush=True)
                continue
        
        # Bulk index
        if actions:
            try:
                response = self.es.bulk(operations=actions)
                indexed = len([item for item in response['items'] if item['index']['status'] in [200, 201]])
                print(f"✓ Indexed {indexed} logs", flush=True)
                return indexed
            except Exception as e:
                print(f"Error bulk indexing: {e}", flush=True)
                return 0
        
        return 0
    
    def run_continuous(self):
        """Continuously index logs from Redis"""
        print("Starting continuous log indexing...", flush=True)
        indexed_total = 0
        
        while True:
            try:
                indexed = self.index_logs_from_redis()
                indexed_total += indexed
                
                # Get index stats
                stats = self.es.count(index=self.index_name)
                total_in_es = stats['count']
                
                print(f"Total in Elasticsearch: {total_in_es:,} | Just indexed: {indexed}", flush=True)
                
                # Wait before next batch
                time.sleep(10)
                
            except KeyboardInterrupt:
                print(f"\nStopping. Total indexed: {indexed_total:,}", flush=True)
                break
            except Exception as e:
                print(f"Error: {e}", flush=True)
                time.sleep(5)

if __name__ == "__main__":
    indexer = ElasticsearchIndexer()
    indexer.run_continuous()