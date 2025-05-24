import pytest
from webhookservice.services.jenkins_service import JenkinsService, BuildResponse
from unittest.mock import patch, Mock

@pytest.fixture
def jenkins_service():
    return JenkinsService("http://jenkins", "user", "token")

@patch("webhookservice.services.jenkins_service.requests.post")
@patch("webhookservice.services.jenkins_service.JenkinsService.get_last_build_number")
def test_trigger_build_success(mock_get_last_build_number, mock_post, jenkins_service):
    mock_post.return_value.status_code = 201
    mock_get_last_build_number.return_value = 42
    resp = jenkins_service.trigger_build("main", "staging", "#chatops")
    assert resp.success is True
    assert resp.build_number == 42
    assert resp.message == "Build triggered successfully"

@patch("webhookservice.services.jenkins_service.requests.post")
def test_trigger_build_fail(mock_post, jenkins_service):
    mock_post.return_value.status_code = 400
    resp = jenkins_service.trigger_build("main", "staging", "#chatops")
    assert resp.success is False
    assert resp.build_number is None
    assert "Failed to trigger build" in resp.message

@patch("webhookservice.services.jenkins_service.requests.post", side_effect=Exception("network error"))
def test_trigger_build_exception(mock_post, jenkins_service):
    resp = jenkins_service.trigger_build("main", "staging", "#chatops")
    assert resp.success is False
    assert resp.build_number is None
    assert "Error triggering Jenkins build" in resp.message

@patch("webhookservice.services.jenkins_service.requests.get")
def test_get_last_build_number_success(mock_get, jenkins_service):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"number": 99}
    num = jenkins_service.get_last_build_number()
    assert num == 99

@patch("webhookservice.services.jenkins_service.requests.get")
def test_get_last_build_number_fail(mock_get, jenkins_service):
    mock_get.return_value.status_code = 404
    num = jenkins_service.get_last_build_number()
    assert num is None

@patch("webhookservice.services.jenkins_service.requests.get")
def test_monitor_build_status_success(mock_get, jenkins_service):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"result": "SUCCESS"}
    result = jenkins_service.monitor_build_status(1, "chan", "main", "staging")
    assert result == "SUCCESS"

@patch("webhookservice.services.jenkins_service.requests.get", side_effect=Exception("err"))
def test_monitor_build_status_exception(mock_get, jenkins_service):
    result = jenkins_service.monitor_build_status(1, "chan", "main", "staging")
    assert result is None 