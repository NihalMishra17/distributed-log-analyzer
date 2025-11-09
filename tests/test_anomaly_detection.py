import pytest
import numpy as np

def test_z_score_calculation():
    """Test Z-score anomaly detection logic"""
    baseline = [100, 105, 98, 102, 99, 103, 101, 100, 104, 102]
    current_value = 150
    
    mean = np.mean(baseline)
    std = np.std(baseline)
    z_score = (current_value - mean) / std
    
    # Should detect as anomaly (z_score > 3)
    assert abs(z_score) > 3

def test_error_rate_spike():
    """Test error rate spike detection"""
    baseline_rate = 0.02  # 2%
    current_rate = 0.15   # 15%
    
    # Should detect spike (5x baseline)
    is_spike = current_rate > (baseline_rate * 5) and current_rate > 0.1
    
    assert is_spike is True

def test_normal_values():
    """Test that normal values are not flagged"""
    baseline = [100, 105, 98, 102, 99, 103, 101, 100, 104, 102]
    current_value = 103
    
    mean = np.mean(baseline)
    std = np.std(baseline)
    z_score = (current_value - mean) / std
    
    # Should NOT detect as anomaly
    assert abs(z_score) <= 3