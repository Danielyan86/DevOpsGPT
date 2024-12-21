import requests
from config.settings import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN


def trigger_jenkins_build(branch, environment):
    """Trigger Jenkins build with parameters using form data"""
    build_url = f"{JENKINS_URL.rstrip('/')}/buildWithParameters"  # Changed to buildWithParameters

    print("\n" + "=" * 50)
    print("=== JENKINS BUILD REQUEST ===")
    print(f"URL: {build_url}")
    print(f"Parameters: branch={branch}, environment={environment}")

    # Use data parameter instead of params for form submission
    response = requests.post(
        build_url,
        auth=(JENKINS_USER, JENKINS_TOKEN),
        data={
            "branch": branch,
            "environment": environment,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    print("\n" + "=" * 50)
    print("=== JENKINS RESPONSE ===")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    return response


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
