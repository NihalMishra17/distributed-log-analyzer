import pytest
import json

def test_metrics_structure():
    """Test metrics response structure"""
    metrics = {
        'total_logs': 1000000,
        'error_logs': 100000,
        'anomalies_detected': 50,
        'last_batch_time': '2025-11-08T23:00:00',
        'error_rate': 10.0,
        'throughput': 16666
    }
    
    assert 'total_logs' in metrics
    assert 'error_logs' in metrics
    assert 'anomalies_detected' in metrics
    assert isinstance(metrics['total_logs'], int)
    assert isinstance(metrics['error_rate'], float)

def test_service_metrics_structure():
    """Test service metrics structure"""
    service_metric = {
        'service_name': 'web-api',
        'total_logs': 200000,
        'error_logs': 20000,
        'avg_response_time': 150.5,
        'error_rate': 10.0
    }
    
    assert 'service_name' in service_metric
    assert 'total_logs' in service_metric
    assert 'avg_response_time' in service_metric
    assert service_metric['error_rate'] >= 0

def test_anomaly_structure():
    """Test anomaly response structure"""
    anomaly = {
        'timestamp': '2025-11-08T23:00:00',
        'service': 'auth-service',
        'type': 'high_latency',
        'value': '373.00ms',
        'z_score': '3.23'
    }
    
    assert 'timestamp' in anomaly
    assert 'service' in anomaly
    assert 'type' in anomaly
    assert 'value' in anomaly