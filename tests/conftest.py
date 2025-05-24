import pytest
from unittest.mock import Mock, patch
import os
import sys

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_slack_client():
    """Mock Slack client fixture"""
    with patch('webhookservice.services.slack_service.SlackClient') as mock:
        yield mock

@pytest.fixture
def mock_jenkins_client():
    """Mock Jenkins client fixture"""
    with patch('webhookservice.services.jenkins_service.Jenkins') as mock:
        yield mock

@pytest.fixture
def mock_prometheus_client():
    """Mock Prometheus client fixture"""
    with patch('webhookservice.services.prometheus_service.requests') as mock:
        yield mock

@pytest.fixture
def mock_dify_client():
    """Mock Dify client fixture"""
    with patch('webhookservice.services.dify_service.requests') as mock:
        yield mock

@pytest.fixture
def sample_slack_message():
    """Sample Slack message fixture"""
    return {
        "type": "message",
        "text": "deploy test version",
        "channel": "test-channel",
        "user": "test-user"
    }

@pytest.fixture
def sample_prometheus_query():
    """Sample Prometheus query fixture"""
    return {
        "query": "cpu_usage",
        "time_range": "5m"
    } 