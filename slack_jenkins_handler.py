from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

# CORS(app)

app = Flask(__name__)
# app.config["SERVER_NAME"] = "*"

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = "xiaodong"
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")

# Add validation to ensure token exists
if not JENKINS_TOKEN:
    raise ValueError("JENKINS_TOKEN environment variable is not set")


@app.route("/slack-handler", methods=["POST"])
def handle_slack_command():
    # Get Slack user input
    user_input = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Parse user input
    params = dict(item.split("=") for item in user_input.split())
    branch = params.get("branch", "main")
    environment = params.get("environment", "staging")

    # Modify Jenkins URL to explicitly hit the build endpoint
    build_url = f"{JENKINS_URL}build"  # Add 'build' to the URL

    print(f"Triggering Jenkins build at: {build_url}")
    print(f"With parameters: branch={branch}, environment={environment}")

    # Call Jenkins API
    try:
        response = requests.post(
            build_url,
            auth=(JENKINS_USER, JENKINS_TOKEN),
            params={  # Changed from data to params
                "branch": branch,
                "environment": environment,
            },
        )

        print(f"Jenkins response status: {response.status_code}")
        print(f"Jenkins response text: {response.text}")

    except Exception as e:
        print(f"Error calling Jenkins: {str(e)}")
        return jsonify({"error": str(e)}), 500

    # Return results
    if response.status_code in [201, 200]:  # Accept both 201 and 200 as success
        return (
            jsonify(
                {
                    "message": f"Jenkins Job triggered! Branch: {branch}, Environment: {environment}"
                }
            ),
            200,
        )
    else:
        return (
            jsonify(
                {
                    "error": f"Failed to trigger Jenkins Job. Status: {response.status_code}, Response: {response.text}"
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
