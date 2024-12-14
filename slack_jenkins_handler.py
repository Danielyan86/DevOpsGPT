from flask import Flask, request, jsonify
import requests
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = "xiaodong"
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

# Add validation to ensure tokens exist
if not JENKINS_TOKEN:
    raise ValueError("JENKINS_TOKEN environment variable is not set")
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable is not set")


@app.route("/slack-handler", methods=["POST"])
def handle_slack_command():
    # Get Slack user input
    user_input = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Parse user input
    params = dict(item.split("=") for item in user_input.split())
    branch = params.get("branch", "main")
    environment = params.get("environment", "staging")

    build_url = f"{JENKINS_URL}build"

    print(f"Triggering Jenkins build at: {build_url}")
    print(f"With parameters: branch={branch}, environment={environment}")

    try:
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

    except Exception as e:
        print(f"Error calling Jenkins: {str(e)}")
        return jsonify({"error": str(e)}), 500

    # Return results to Slack
    if response.status_code in [201, 200]:
        slack_message = (
            f"Jenkins Job triggered! Branch: {branch}, Environment: {environment}"
        )
    else:
        slack_message = f"Failed to trigger Jenkins Job. Error: {response.text}"

    # Send message to Slack using environment variable
    slack_response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel_id, "text": slack_message},
    )

    if slack_response.status_code == 200:
        return jsonify({"text": "Message sent to Slack!"}), 200
    else:
        return jsonify({"text": "Failed to send message to Slack."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
