import os

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = "xiaodong"
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

# Dify Configuration
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_ENDPOINT = "http://127.0.0.1/v1/chat-messages"

# Flask Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = True


def validate_config():
    """Validate required environment variables"""
    if not JENKINS_TOKEN:
        raise ValueError("JENKINS_TOKEN environment variable is not set")
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN environment variable is not set")
    if not DIFY_API_KEY:
        raise ValueError("DIFY_API_KEY environment variable is not set")
