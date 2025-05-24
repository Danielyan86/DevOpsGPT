import pytest
from unittest.mock import patch, MagicMock
from webhookservice.services.prometheus_service import PrometheusService

@pytest.fixture
def mock_prometheus_client():
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def sample_prometheus_query():
    return {
        "query": "cpu_usage",
        "time_range": "5m"
    }

def test_prometheus_service_initialization():
    """Test Prometheus service initialization"""
    service = PrometheusService()
    assert service.base_url is not None
    assert service.api_url is not None

def test_query(mock_prometheus_client):
    """Test instant query"""
    service = PrometheusService()
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"instance": "localhost:9090"},
                    "value": [1620000000, "0.5"]
                }
            ]
        }
    }
    mock_prometheus_client.return_value.json.return_value = mock_response
    
    result = service.query("cpu_usage")
    
    assert result["status"] == "success"
    assert "data" in result
    mock_prometheus_client.assert_called_once()

def test_query_range(mock_prometheus_client):
    """Test range query"""
    service = PrometheusService()
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"instance": "localhost:9090"},
                    "values": [[1620000000, "0.5"], [1620000060, "0.6"]]
                }
            ]
        }
    }
    mock_prometheus_client.return_value.json.return_value = mock_response
    
    result = service.query_range(
        query="cpu_usage",
        start="2024-01-01T00:00:00Z",
        end="2024-01-01T01:00:00Z",
        step="1m"
    )
    
    assert result["status"] == "success"
    assert "data" in result
    mock_prometheus_client.assert_called_once()

def test_get_process_metrics(mock_prometheus_client):
    """Test getting process metrics"""
    service = PrometheusService()
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"instance": "localhost:9090"},
                    "value": [1620000000, "0.5"]
                }
            ]
        }
    }
    mock_prometheus_client.return_value.json.return_value = mock_response
    
    result = service.get_process_metrics("cpu")
    
    assert isinstance(result, dict)
    assert "cpu_usage" in result

def test_get_metrics_range(mock_prometheus_client):
    """Test getting metrics range"""
    service = PrometheusService()
    mock_response = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"instance": "localhost:9090"},
                    "values": [[1620000000, "0.5"], [1620000060, "0.6"]]
                }
            ]
        }
    }
    mock_prometheus_client.return_value.json.return_value = mock_response
    
    result = service.get_metrics_range("cpu_usage", hours=1.0)
    
    assert result["status"] == "success"
    assert "data" in result
    mock_prometheus_client.assert_called_once()

def test_query_error_handling(mock_prometheus_client):
    """Test error handling in query"""
    service = PrometheusService()
    mock_prometheus_client.side_effect = Exception("Prometheus API Error")
    
    with pytest.raises(Exception) as exc_info:
        service.query("cpu_usage")
    
    assert "Prometheus API Error" in str(exc_info.value) 