import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from webhookservice.services.dify_service import (
    handle_dify_api_errors,
    make_dify_request,
    parse_deployment_intent,
    parse_monitoring_intent,
    send_metrics_to_dify
)

@pytest.fixture
def mock_response():
    response = MagicMock()
    response.status_code = 200
    response.iter_lines.return_value = [
        b'data: {"event": "agent_thought", "thought": "{\\"branch\\": \\"main\\", \\"environment\\": \\"staging\\"}"}',
        b'data: {"event": "end", "answer": "Deployment initiated"}'
    ]
    return response

def test_handle_dify_api_errors_success():
    @handle_dify_api_errors
    def test_func():
        return {"success": True}
    
    result = test_func()
    assert result == {"success": True}

def test_handle_dify_api_errors_timeout():
    @handle_dify_api_errors
    def test_func():
        raise requests.Timeout()
    
    result = test_func()
    assert result == {"error": "Request timed out"}

@patch('requests.post')
def test_make_dify_request(mock_post, mock_response):
    mock_post.return_value = mock_response
    
    response = make_dify_request("test_api_key", "test message")
    
    assert response.status_code == 200
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]
    assert call_args['headers']['Authorization'] == 'Bearer test_api_key'
    assert 'test message' in call_args['data']

@patch('webhookservice.services.dify_service.make_dify_request')
def test_parse_deployment_intent(mock_make_request, mock_response):
    mock_make_request.return_value = mock_response
    
    result = parse_deployment_intent("Deploy to staging")
    
    assert isinstance(result, dict)
    assert "branch" in result
    assert "environment" in result
    assert result["branch"] == "main"
    assert result["environment"] == "staging"

@patch('webhookservice.services.dify_service.make_dify_request')
def test_parse_monitoring_intent(mock_make_request):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_lines.return_value = [
        b'data: {"event": "agent_thought", "thought": "{\\"type\\": \\"monitoring\\", \\"query_type\\": \\"current\\", \\"metric\\": \\"cpu_usage\\", \\"hours\\": 1}"}',
        b'data: {"event": "end", "answer": "Metrics analysis"}'
    ]
    mock_make_request.return_value = mock_response
    
    result = parse_monitoring_intent("Show me CPU usage")
    
    assert isinstance(result, dict)
    assert result["type"] == "monitoring"
    assert result["query_type"] == "current"
    assert result["metric"] == "cpu_usage"
    assert result["hours"] == 1
    assert "original_message" in result

@patch('webhookservice.services.dify_service.make_dify_request')
def test_send_metrics_to_dify(mock_make_request, mock_response):
    mock_make_request.return_value = mock_response
    
    metrics = {
        "cpu_usage": 75.5,
        "memory_usage": 60.2
    }
    
    result = send_metrics_to_dify(metrics)
    
    assert isinstance(result, dict)
    mock_make_request.assert_called_once() 