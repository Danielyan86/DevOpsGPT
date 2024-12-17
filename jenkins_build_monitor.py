from flask import Flask, request, jsonify
import requests
import os
import time
from flask_cors import CORS
import json
from typing import Dict, Optional
from threading import Thread

app = Flask(__name__)
CORS(app)

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = "xiaodong"
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

if not JENKINS_TOKEN:
    raise ValueError("JENKINS_TOKEN environment variable is not set")
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN environment variable is not set")

# Update Dify configuration
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_ENDPOINT = "http://127.0.0.1/v1/chat-messages"  # Updated endpoint

if not DIFY_API_KEY:
    raise ValueError("DIFY_API_KEY environment variable is not set")


def parse_deployment_intent(message: str) -> Optional[Dict]:
    """Parse natural language deployment request using local Dify API"""
    try:
        print(f"\n=== Processing Natural Language Request ===")
        print(f"Input message: {message}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DIFY_API_KEY}",
        }

        payload = json.dumps(
            {
                "inputs": {},
                "query": message,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "chatops-user",
                "files": [],
            }
        )

        print(f"Sending request to Dify with payload: {payload}")

        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,  # Enable streaming
        )

        print(f"Dify API Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error from Dify API: {response.text}")
            return None

        # Process streaming response
        full_response = ""
        thought_content = None

        for line in response.iter_lines():
            if line:
                # Remove 'data: ' prefix
                line = line.decode("utf-8").replace("data: ", "")

                try:
                    data = json.loads(line)

                    # Look for the thought event which contains the parsed parameters
                    if data.get("event") == "agent_thought":
                        thought_content = data.get("thought", "")
                        if thought_content:
                            try:
                                thought_json = json.loads(thought_content)
                                parameters = thought_json.get("parameters", {})

                                # Extract deployment parameters
                                parsed_params = {
                                    "branch": parameters.get("branch", "main"),
                                    "environment": parameters.get(
                                        "environment", "staging"
                                    ),
                                }

                                print(f"Parsed parameters: {parsed_params}")
                                return parsed_params

                            except json.JSONDecodeError as e:
                                print(f"Error parsing thought content: {e}")
                                continue

                except json.JSONDecodeError:
                    continue

        print("No valid parameters found in response")
        return None

    except Exception as e:
        print(f"Error in parse_deployment_intent: {str(e)}")
        print(f"Exception type: {type(e)}")
        return None


def send_slack_message(channel_id, message):
    """Send message to Slack channel"""
    try:
        print(f"\n=== Sending Slack Message ===")
        print(f"Channel: {channel_id}")
        print(f"Message content: {message}")

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={
                "channel": channel_id,
                "text": message,
                "mrkdwn": True,
                "response_type": "in_channel",
            },
        )

        print(f"Slack API Response Status: {response.status_code}")
        print(f"Slack API Response Body: {response.text}")

        response_data = response.json()
        if not response_data.get("ok"):
            error = response_data.get("error", "unknown error")
            if error == "not_in_channel":
                print(f"ERROR: Bot needs to be invited to channel {channel_id}")
                # Optionally, try to join the channel if bot has the right permissions
                join_response = requests.post(
                    "https://slack.com/api/conversations.join",
                    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                    json={"channel": channel_id},
                )
                print(f"Channel join attempt response: {join_response.text}")
                # Try sending the message again
                return send_slack_message(channel_id, message)
            else:
                print(f"ERROR: Slack API error: {error}")

        return response_data.get("ok", False)
    except Exception as e:
        print(f"ERROR in send_slack_message: {str(e)}")
        print(f"Exception type: {type(e)}")
        return False


@app.route("/slack-handler", methods=["POST"])
def handle_slack_command():
    user_input = request.form.get("text")
    channel_id = request.form.get("channel_id")

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

        if response.status_code in [201, 200]:
            build_number = get_last_build_number()
            if build_number:
                # Start monitoring in a separate thread
                from threading import Thread

                Thread(
                    target=monitor_build_status,
                    args=(build_number, channel_id, branch, environment),
                    daemon=True,
                ).start()

                # Return immediate response to make it visible in channel
                return (
                    jsonify(
                        {
                            "response_type": "in_channel",
                            "text": f"🚀 Starting deployment process...\nBuild #{build_number}\nBranch: {branch}\nEnvironment: {environment}",
                        }
                    ),
                    200,
                )
            else:
                error_msg = "❌ Could not determine build number"
                send_slack_message(channel_id, error_msg)
                return jsonify({"response_type": "in_channel", "text": error_msg}), 500
        else:
            error_msg = (
                f" Failed to trigger Jenkins Job. Status: {response.status_code}"
            )
            send_slack_message(channel_id, error_msg)
            return jsonify({"response_type": "in_channel", "text": error_msg}), 500

    except Exception as e:
        error_msg = f"❌ Error calling Jenkins: {str(e)}"
        send_slack_message(channel_id, error_msg)
        return jsonify({"response_type": "in_channel", "text": error_msg}), 500


@app.route("/chat-deploy", methods=["POST"])
def handle_natural_language_deploy():
    """Handle natural language deployment requests"""
    try:
        # Get content type and parse request
        content_type = request.headers.get('Content-Type', '').lower()
        print(f"Received Content-Type: {content_type}")

        # Parse request data based on content type
        if 'application/json' in content_type:
            request_data = request.get_json()
        elif 'application/x-www-form-urlencoded' in content_type:
            request_data = {
                'message': request.form.get('text', request.form.get('message')),
                'channel_id': request.form.get('channel_id')
            }
        else:
            return jsonify({
                "error": "Content-Type must be application/json or application/x-www-form-urlencoded",
                "received": content_type
            }), 415

        # Validate message
        if not request_data or not request_data.get('message'):
            return jsonify({
                "error": "Missing 'message' or 'text' in request"
            }), 400

        # Parse deployment intent
        deployment_params = parse_deployment_intent(request_data['message'])
        if not deployment_params:
            return jsonify({"error": "Could not understand deployment request"}), 400

        # Trigger Jenkins build
        print(f"\n=== Triggering Jenkins Build ===")
        print(f"Parameters: {deployment_params}")
        
        build_url = f"{JENKINS_URL.rstrip('/')}/build"
        response = requests.post(
            build_url,
            auth=(JENKINS_USER, JENKINS_TOKEN),
            params=deployment_params
        )

        if response.status_code not in [201, 200]:
            return jsonify({
                "error": f"Failed to trigger Jenkins build: {response.status_code}"
            }), 500

        # Return success response
        return jsonify({
            "success": True,
            "message": "Deployment triggered successfully",
            "parameters": deployment_params,
            "jenkins_url": JENKINS_URL
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": f"Error processing deployment request: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
