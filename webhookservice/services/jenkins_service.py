import requests
from config.settings import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN


def trigger_jenkins_build(
    branch: str, environment: str, channel: str = "#chatops"
) -> requests.Response:
    """Trigger Jenkins build with parameters"""
    params = {"branch": branch, "environment": environment, "SLACK_CHANNEL": channel}

    print("\n" + "=" * 50)
    print("=== TRIGGERING JENKINS BUILD ===")
    print(f"URL: {JENKINS_URL.rstrip('/')}/buildWithParameters")
    print("Parameters:")
    print(f"• Branch: {params['branch']}")
    print(f"• Environment: {params['environment']}")
    print(f"• Slack Channel: {params['SLACK_CHANNEL']}")
    print("=" * 50 + "\n")

    try:
        response = requests.post(
            f"{JENKINS_URL.rstrip('/')}/buildWithParameters",
            params=params,
            auth=(JENKINS_USER, JENKINS_TOKEN),
        )

        print("=== JENKINS RESPONSE ===")
        print(f"Status Code: {response.status_code}")
        print(
            f"Response: {response.text[:200]}..."
        )  # Print first 200 chars of response
        print("=" * 50 + "\n")

        return response
    except Exception as e:
        print("=== JENKINS ERROR ===")
        print(f"Error: {str(e)}")
        print("=" * 50 + "\n")
        raise


def get_last_build_number():
    """Get the last build number from Jenkins"""
    try:
        api_url = f"{JENKINS_URL.rstrip('/')}/lastBuild/api/json"
        response = requests.get(api_url, auth=(JENKINS_USER, JENKINS_TOKEN))
        if response.status_code == 200:
            return response.json().get("number")
        return None
    except Exception as e:
        print(f"Error getting last build number: {e}")
        return None


def monitor_build_status(build_number, channel_id, branch, environment):
    """Monitor build status"""
    try:
        api_url = f"{JENKINS_URL.rstrip('/')}/{build_number}/api/json"
        response = requests.get(api_url, auth=(JENKINS_USER, JENKINS_TOKEN))
        if response.status_code == 200:
            build_info = response.json()
            return build_info.get("result")
        return None
    except Exception as e:
        print(f"Error monitoring build status: {e}")
        return None
