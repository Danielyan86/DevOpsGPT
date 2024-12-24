from pydantic import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings"""

    SLACK_BOT_DEPLOY_TOKEN: str = os.getenv("SLACK_BOT_DEPLOY_TOKEN")
    SLACK_BOT_MONITOR_TOKEN: str = os.getenv("SLACK_BOT_MONITOR_TOKEN")
    JENKINS_URL: str = os.getenv("JENKINS_URL", "http://localhost:8080")
    JENKINS_USER: str = os.getenv("JENKINS_USER")
    JENKINS_TOKEN: str = os.getenv("JENKINS_TOKEN")
    DIFY_API_ENDPOINT: str = os.getenv("DIFY_API_ENDPOINT")
    DIFY_DEPLOY_BOT_API_KEY: str = os.getenv("DIFY_DEPLOY_BOT_API_KEY")
    DIFY_MONITOR_BOT_API_KEY: str = os.getenv("DIFY_MONITOR_BOT_API_KEY")
    PROMETHEUS_BASE_URL: str = os.getenv("PROMETHEUS_BASE_URL")

    @classmethod
    def validate(cls):
        config = cls()
        missing = [field for field, value in config.__dict__.items() if value is None]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        return config
