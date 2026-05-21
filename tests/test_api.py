"""API endpoint tests."""

import os
import sys
from pathlib import Path

import pytest

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

# Create required directories
Path("logs").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("models").mkdir(exist_ok=True)

from fastapi.testclient import TestClient

# Set environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "ERROR"

from src.nids.api.main_v2 import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_features():
    """Create sample feature data."""
    return {
        "flow_duration": 1000.0,
        "total_fwd_packets": 10,
        "total_bwd_packets": 5,
        "total_length_fwd_packets": 5000.0,
        "total_length_bwd_packets": 2500.0,
        "fwd_packet_length_mean": 500.0,
        "fwd_packet_length_std": 100.0,
        "bwd_packet_length_mean": 500.0,
        "bwd_packet_length_std": 100.0,
        "flow_bytes_per_sec": 7500.0,
        "flow_packets_per_sec": 15.0,
        "flow_iat_mean": 100.0,
        "flow_iat_std": 50.0,
        "flow_iat_max": 500.0,
        "fwd_iat_total": 1000.0,
        "fwd_iat_mean": 100.0,
        "fwd_iat_std": 50.0,
        "bwd_iat_total": 500.0,
        "bwd_iat_mean": 100.0,
        "bwd_iat_std": 50.0,
        "fwd_packets_per_sec": 10.0,
        "bwd_packets_per_sec": 5.0,
        "down_up_ratio": 0.5,
        "avg_packet_size": 500.0,
        "avg_fwd_segment_size": 500.0,
        "avg_bwd_segment_size": 500.0,
        "subflow_fwd_packets": 10,
        "subflow_bwd_packets": 5,
        "subflow_fwd_bytes": 5000.0,
        "subflow_bwd_bytes": 2500.0,
    }


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "running"


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "model_loaded" in data
    assert "uptime_seconds" in data


@pytest.mark.skipif(not Path("models/nids_model.pkl").exists(), reason="Model not trained")
def test_predict_endpoint_invalid_ip(client, sample_features):
    """Test prediction with invalid IP address."""
    request_data = {
        "features": sample_features,
        "src_ip": "999.999.999.999",
        "dst_ip": "192.168.1.1",
    }
    response = client.post("/predict", json=request_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.skipif(not Path("models/nids_model.pkl").exists(), reason="Model not trained")
def test_predict_endpoint_negative_values(client, sample_features):
    """Test prediction with negative feature values."""
    sample_features["flow_duration"] = -1000.0
    request_data = {
        "features": sample_features,
        "src_ip": "192.168.1.1",
        "dst_ip": "10.0.0.1",
    }
    response = client.post("/predict", json=request_data)
    assert response.status_code == 422  # Validation error


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "performance" in data
    assert "attack_distribution" in data


def test_prometheus_endpoint(client):
    """Test Prometheus scrape endpoint."""
    response = client.get("/prometheus")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert b"nids_requests" in response.content


def test_stats_endpoint(client):
    """Test stats endpoint."""
    response = client.get("/stats")
    # Can be 200 or 503 depending on model availability
    assert response.status_code in [200, 400, 503]


def test_alerts_endpoint(client):
    """Test alerts endpoint."""
    response = client.get("/alerts?limit=5")
    # Can be 200 or 503 depending on model availability
    assert response.status_code in [200, 400, 503]


def test_reset_metrics_endpoint(client):
    """Test reset metrics endpoint."""
    response = client.post("/reset-metrics")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
