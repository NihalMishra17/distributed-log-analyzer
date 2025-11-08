from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional, List
import redis
import json
from jose import JWTError, jwt
from pydantic import BaseModel

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(
    title="Distributed Log Analyzer API",
    description="REST API for real-time log analysis and anomaly detection",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your dashboard domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

# Security
security = HTTPBearer()

# Pydantic Models
class Token(BaseModel):
    access_token: str
    token_type: str

class SystemMetrics(BaseModel):
    total_logs: int
    error_logs: int
    anomalies_detected: int
    last_batch_time: Optional[str]
    error_rate: float
    throughput: int

class ServiceMetrics(BaseModel):
    service_name: str
    total_logs: int
    error_logs: int
    avg_response_time: float
    error_rate: float

class Anomaly(BaseModel):
    timestamp: str
    service: str
    type: str
    value: str
    z_score: Optional[str] = None
    description: Optional[str] = None

class LogEntry(BaseModel):
    timestamp: str
    service: str
    level: str
    message: str
    response_time_ms: int
    user_id: str
    request_id: str
    ip_address: str
    endpoint: str

class WebhookRequest(BaseModel):
    url: str
    events: List[str]  # ['anomaly_detected', 'high_error_rate']

# Authentication helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Routes
@app.get("/")
def root():
    return {
        "message": "Distributed Log Analyzer API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

@app.get("/health")
def health_check():
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except:
        return {"status": "unhealthy", "redis": "disconnected"}

@app.post("/api/v1/auth/token", response_model=Token)
def login(username: str, password: str):
    # Simple auth for demo - in production, use proper user management
    if username == "admin" and password == "admin123":
        access_token = create_access_token(data={"sub": username})
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Incorrect username or password")

@app.get("/api/v1/metrics", response_model=SystemMetrics)
def get_system_metrics(token: dict = Depends(verify_token)):
    """Get overall system metrics"""
    metrics = redis_client.hgetall('metrics')
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics available")
    
    total_logs = int(metrics.get('total_logs', 0))
    error_logs = int(metrics.get('error_logs', 0))
    error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
    throughput = total_logs // 60 if total_logs > 0 else 0
    
    return SystemMetrics(
        total_logs=total_logs,
        error_logs=error_logs,
        anomalies_detected=int(metrics.get('anomalies_detected', 0)),
        last_batch_time=metrics.get('last_batch_time'),
        error_rate=round(error_rate, 2),
        throughput=throughput
    )

@app.get("/api/v1/services", response_model=List[ServiceMetrics])
def get_all_services(token: dict = Depends(verify_token)):
    """Get metrics for all services"""
    services = ['web-api', 'auth-service', 'payment-service', 'database', 'cache-service']
    service_metrics = []
    
    for service in services:
        metrics = redis_client.hgetall(f'service:{service}')
        if metrics:
            total_logs = int(metrics.get('total_logs', 0))
            error_logs = int(metrics.get('error_logs', 0))
            error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
            
            service_metrics.append(ServiceMetrics(
                service_name=service,
                total_logs=total_logs,
                error_logs=error_logs,
                avg_response_time=float(metrics.get('avg_response_time', 0)),
                error_rate=round(error_rate, 2)
            ))
    
    return service_metrics

@app.get("/api/v1/services/{service_name}", response_model=ServiceMetrics)
def get_service_metrics(service_name: str, token: dict = Depends(verify_token)):
    """Get metrics for a specific service"""
    metrics = redis_client.hgetall(f'service:{service_name}')
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    total_logs = int(metrics.get('total_logs', 0))
    error_logs = int(metrics.get('error_logs', 0))
    error_rate = (error_logs / total_logs * 100) if total_logs > 0 else 0
    
    return ServiceMetrics(
        service_name=service_name,
        total_logs=total_logs,
        error_logs=error_logs,
        avg_response_time=float(metrics.get('avg_response_time', 0)),
        error_rate=round(error_rate, 2)
    )

@app.get("/api/v1/anomalies", response_model=List[Anomaly])
def get_anomalies(limit: int = 10, token: dict = Depends(verify_token)):
    """Get recent anomalies"""
    anomalies_raw = redis_client.lrange('anomalies', 0, limit - 1)
    
    anomalies = []
    for anomaly_str in anomalies_raw:
        try:
            anomaly_data = json.loads(anomaly_str)
            anomalies.append(Anomaly(**anomaly_data))
        except:
            continue
    
    return anomalies

@app.get("/api/v1/logs", response_model=List[LogEntry])
def get_recent_logs(limit: int = 20, service: Optional[str] = None, token: dict = Depends(verify_token)):
    """Get recent log entries"""
    logs_raw = redis_client.lrange('recent_logs', 0, limit - 1)
    
    logs = []
    for log_str in logs_raw:
        try:
            log_data = json.loads(log_str)
            # Filter by service if specified
            if service and log_data.get('service') != service:
                continue
            logs.append(LogEntry(**log_data))
        except:
            continue
    
    return logs

@app.post("/api/v1/webhooks")
def register_webhook(webhook: WebhookRequest, token: dict = Depends(verify_token)):
    """Register a webhook for notifications"""
    # Store webhook in Redis
    webhook_id = f"webhook:{webhook.url}"
    redis_client.hset(webhook_id, mapping={
        'url': webhook.url,
        'events': json.dumps(webhook.events),
        'created_at': datetime.utcnow().isoformat()
    })
    
    return {
        "status": "registered",
        "webhook_id": webhook_id,
        "url": webhook.url,
        "events": webhook.events
    }

@app.get("/api/v1/webhooks")
def list_webhooks(token: dict = Depends(verify_token)):
    """List all registered webhooks"""
    webhook_keys = redis_client.keys('webhook:*')
    webhooks = []
    
    for key in webhook_keys:
        webhook_data = redis_client.hgetall(key)
        webhooks.append({
            'id': key,
            'url': webhook_data.get('url'),
            'events': json.loads(webhook_data.get('events', '[]')),
            'created_at': webhook_data.get('created_at')
        })
    
    return webhooks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)