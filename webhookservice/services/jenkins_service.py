import requests
from config.settings import JENKINS_URL, JENKINS_USER, JENKINS_TOKEN

def trigger_jenkins_build(branch, environment):
    build_url = f"{JENKINS_URL.rstrip('/')}/build"
    
    print(f"Triggering Jenkins build at: {build_url}")
    print(f"With parameters: branch={branch}, environment={environment}")
    
    response = requests.post(
        build_url,
        auth=(JENKINS_USER, JENKINS_TOKEN),
        params={
            "branch": branch,
            "environment": environment,
        },
    )
    
    print(f"Jenkins response status: {response.status_code}")
    print(f"Jenkins response text: {response.text}")
    
    return response

def get_last_build_number():
    # Implement this based on your Jenkins API
    pass

def monitor_build_status(build_number, channel_id, branch, environment):
    # Implement this based on your Jenkins API
    pass
