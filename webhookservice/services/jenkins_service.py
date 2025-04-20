import requests
from config.settings import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN
from dataclasses import dataclass
from typing import Optional, Dict, Any
from requests import Response
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BuildResponse:
    success: bool
    build_number: Optional[int]
    message: str
    data: Optional[Dict[str, Any]] = None


class JenkinsService:
    def __init__(self, url: str, user: str, token: str):
        self.url = url.rstrip("/")
        self.auth = (user, token)

    def trigger_build(
        self, branch: str, environment: str, channel: str = "#chatops"
    ) -> BuildResponse:
        try:
            logger.info(f"Attempting to trigger Jenkins build with parameters:")
            logger.info(f"- Branch: {branch}")
            logger.info(f"- Environment: {environment}")
            logger.info(f"- Channel: {channel}")
            logger.info(f"- Jenkins URL: {self.url}")

            params = {
                "branch": branch,
                "environment": environment,
                "SLACK_CHANNEL": channel,
            }

            logger.info(
                f"Sending POST request to {self.url}/buildWithParameters with params: {params}"
            )
            response = requests.post(
                f"{self.url}/buildWithParameters", params=params, auth=self.auth
            )

            logger.info(f"Jenkins API response status code: {response.status_code}")
            logger.info(f"Jenkins API response text: {response.text}")

            if response.status_code in (200, 201):
                build_number = self.get_last_build_number()
                logger.info(
                    f"Build triggered successfully. Build number: {build_number}"
                )
                return BuildResponse(
                    success=True,
                    build_number=build_number,
                    message="Build triggered successfully",
                )

            error_msg = f"Failed to trigger build: {response.status_code}"
            logger.error(error_msg)
            return BuildResponse(
                success=False,
                build_number=None,
                message=error_msg,
            )

        except Exception as e:
            error_msg = f"Error triggering Jenkins build: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return BuildResponse(success=False, build_number=None, message=error_msg)

    def get_last_build_number(self):
        """Get the last build number from Jenkins"""
        try:
            api_url = f"{self.url}/lastBuild/api/json"
            response = requests.get(api_url, auth=self.auth)
            if response.status_code == 200:
                return response.json().get("number")
            return None
        except Exception as e:
            logger.error(f"Error getting last build number: {e}")
            return None

    def monitor_build_status(self, build_number, channel_id, branch, environment):
        """Monitor build status"""
        try:
            api_url = f"{self.url}/{build_number}/api/json"
            response = requests.get(api_url, auth=self.auth)
            if response.status_code == 200:
                build_info = response.json()
                return build_info.get("result")
            return None
        except Exception as e:
            logger.error(f"Error monitoring build status: {e}")
            return None


# Create a singleton instance for global use
jenkins_service = JenkinsService(JENKINS_URL, JENKINS_USER, JENKINS_TOKEN)


# Function-based interface for backward compatibility
def trigger_jenkins_build(
    branch: str, environment: str, channel: str = "#chatops"
) -> BuildResponse:
    """Trigger Jenkins build with parameters"""
    return jenkins_service.trigger_build(branch, environment, channel)


def get_last_build_number():
    """Get the last build number from Jenkins"""
    return jenkins_service.get_last_build_number()


def monitor_build_status(build_number, channel_id, branch, environment):
    """Monitor build status"""
    return jenkins_service.monitor_build_status(
        build_number, channel_id, branch, environment
    )
