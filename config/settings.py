import os
import logging

# Set logging level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = os.environ.get("JENKINS_USER")
if not JENKINS_USER:
    raise ValueError("JENKINS_USER environment variable is not set")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")

# Slack Configuration
SLACK_BOT_DEPLOY_TOKEN = os.environ.get("SLACK_BOT_DEPLOY_TOKEN")
SLACK_BOT_MONITOR_TOKEN = os.environ.get("SLACK_BOT_MONITOR_TOKEN")

# Dify Configuration
DIFY_DEPLOY_BOT_API_KEY = os.environ.get("DIFY_DEPLOY_BOT_API_KEY", "")
DIFY_API_ENDPOINT = os.environ.get("DIFY_API_ENDPOINT")
DIFY_MONITOR_BOT_API_KEY = os.environ.get("DIFY_MONITOR_BOT_API_KEY", "")

# Prometheus Configuration
PROMETHEUS_BASE_URL = os.environ.get("PROMETHEUS_BASE_URL")

# Flask Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = True


def validate_config():
    """Validate required environment variables"""
    if not JENKINS_TOKEN:
        raise ValueError("JENKINS_TOKEN environment variable is not set")
    if not SLACK_BOT_DEPLOY_TOKEN:
        raise ValueError("SLACK_BOT_DEPLOY_TOKEN environment variable is not set")
    if not SLACK_BOT_MONITOR_TOKEN:
        raise ValueError("SLACK_BOT_MONITOR_TOKEN environment variable is not set")
    if not DIFY_DEPLOY_BOT_API_KEY:
        raise ValueError("DIFY_DEPLOY_BOT_API_KEY environment variable is not set")
    if not DIFY_MONITOR_BOT_API_KEY:
        raise ValueError("DIFY_MONITOR_BOT_API_KEY environment variable is not set")
    if not DIFY_API_ENDPOINT:
        raise ValueError("DIFY_API_ENDPOINT environment variable is not set")
    if not PROMETHEUS_BASE_URL:
        raise ValueError("PROMETHEUS_BASE_URL environment variable is not set")
