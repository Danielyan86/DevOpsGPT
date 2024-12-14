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
    user_input = request.form.get("text")  # Example: "branch=main environment=staging"
    channel_id = request.form.get("channel_id")

    # Parse user input
    params = dict(item.split("=") for item in user_input.split())
    branch = params.get("branch", "main")
    environment = params.get("environment", "staging")

    # Call Jenkins API
    response = requests.post(
        JENKINS_URL,
        auth=(JENKINS_USER, JENKINS_TOKEN),
        data={"branch": branch, "environment": environment},
    )

    # Return results to Slack
    if response.status_code == 201:
        slack_message = (
            f"Jenkins Job triggered! Branch: {branch}, Environment: {environment}"
        )
    else:
        slack_message = f"Failed to trigger Jenkins Job. Error: {response.text}"

    # Send message to Slack
    slack_response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer xoxb-your-slack-bot-token"},
        json={"channel": channel_id, "text": slack_message},
    )

    if slack_response.status_code == 200:
        return jsonify({"text": "Message sent to Slack!"}), 200
    else:
        return jsonify({"text": "Failed to send message to Slack."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
