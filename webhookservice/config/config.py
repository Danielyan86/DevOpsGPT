import os
from dataclasses import dataclass


@dataclass
class Config:
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN")
    JENKINS_URL: str = os.getenv("JENKINS_URL")
    JENKINS_USER: str = os.getenv("JENKINS_USER")
    JENKINS_TOKEN: str = os.getenv("JENKINS_TOKEN")
    DIFY_API_KEY: str = os.getenv("DIFY_API_KEY")
    DIFY_API_ENDPOINT: str = os.getenv("DIFY_API_ENDPOINT")

    @classmethod
    def validate(cls):
        config = cls()
        missing = [field for field, value in config.__dict__.items() if value is None]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        return config
