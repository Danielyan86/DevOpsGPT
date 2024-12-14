from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Jenkins Configuration
JENKINS_URL = "http://localhost:8080/job/<job-name>/buildWithParameters"
JENKINS_USER = "admin"
JENKINS_TOKEN = "<your-token>"


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
    app.run(port=5000, debug=True)
