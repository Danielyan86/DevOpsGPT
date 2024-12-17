from flask import Flask, request, jsonify
import requests
import os
import time
from flask_cors import CORS
import json
from typing import Dict, Optional

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


def get_last_build_number():
    """Get the last build number from Jenkins"""
    try:
        api_url = f"{JENKINS_URL}api/json"
        response = requests.get(api_url, auth=(JENKINS_USER, JENKINS_TOKEN))
        if response.status_code == 200:
            data = response.json()
            return data.get("lastBuild", {}).get("number")
    except Exception as e:
        print(f"Error getting last build number: {str(e)}")
    return None


def get_build_status(build_number):
    """Get the status of a specific build"""
    try:
        status_url = f"{JENKINS_URL}{build_number}/api/json"
        print(f"Checking build status at: {status_url}")

        response = requests.get(status_url, auth=(JENKINS_USER, JENKINS_TOKEN))

        if response.status_code == 200:
            data = response.json()
            print(f"Build status response: {data}")  # Add debug print
            return data
        else:
            print(f"Error getting build status. Status code: {response.status_code}")
            print(f"Response text: {response.text}")
            return None
    except Exception as e:
        print(f"Error in get_build_status: {str(e)}")
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


def monitor_build_status(build_number, channel_id, branch, environment):
    """Monitor build status and send updates to Slack"""
    max_attempts = 30
    attempt = 0
    last_progress = -1
    check_interval = 5  # Reduce check interval to 5 seconds

    print(f"\n=== Starting Build Monitor ===")
    print(f"Build: #{build_number}")
    print(f"Channel: {channel_id}")
    print(f"Branch: {branch}")
    print(f"Environment: {environment}")

    while attempt < max_attempts:
        try:
            print(
                f"\n=== Checking Build Status (Attempt {attempt + 1}/{max_attempts}) ==="
            )
            status_info = get_build_status(build_number)

            if status_info:
                current_status = status_info.get("building", True)
                duration = status_info.get("duration", 0) / 1000
                estimated_duration = status_info.get("estimatedDuration", 0) / 1000

                # Calculate progress based on actual duration if building is done
                if not current_status:
                    progress = 100
                else:
                    elapsed_time = attempt * check_interval
                    progress = min(100, int((elapsed_time / estimated_duration) * 100))
                    # Force at least one intermediate progress update
                    if progress > 80:
                        progress = 80

                print(f"\n=== Progress Calculation Details ===")
                print(f"Current build status: building={current_status}")
                print(f"Actual duration: {duration:.2f} seconds")
                print(f"Estimated duration: {estimated_duration:.0f} seconds")
                print(
                    f"Elapsed time: {elapsed_time if current_status else duration:.2f} seconds"
                )
                print(f"Progress: {progress}%")

                # Send progress update more frequently
                if progress != last_progress:
                    print(f"\n=== Preparing Progress Message ===")

                    # Create progress bar visualization
                    filled_blocks = "█" * (progress // 10)
                    empty_blocks = "▒" * ((100 - progress) // 10)
                    progress_bar = filled_blocks + empty_blocks

                    progress_blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"🔄 *Build In Progress*\n"
                                    f"• Build: #{build_number}\n"
                                    f"• Branch: {branch}\n"
                                    f"• Environment: {environment}\n"
                                    f"• Status: Building...\n"
                                    f"• Time elapsed: {elapsed_time if current_status else duration:.2f} seconds\n"
                                    f"• Estimated duration: {estimated_duration:.0f} seconds"
                                ),
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"• Progress: {progress}%\n" f"{progress_bar}"
                                ),
                            },
                        },
                    ]

                    # Send message with blocks
                    response = requests.post(
                        "https://slack.com/api/chat.postMessage",
                        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                        json={
                            "channel": channel_id,
                            "blocks": progress_blocks,
                            "text": f"Build Progress: {progress}%",
                        },
                    )

                    last_progress = progress

                if not current_status:
                    print("\n=== Build Completed ===")
                    result = status_info.get("result", "UNKNOWN")
                    duration = status_info.get("duration", 0) / 1000
                    display_name = status_info.get("displayName", f"#{build_number}")

                    print(f"Result: {result}")
                    print(f"Duration: {duration:.2f} seconds")

                    # Get Git information
                    git_info = next(
                        (
                            action
                            for action in status_info.get("actions", [])
                            if action.get("_class", "").endswith("BuildData")
                        ),
                        {},
                    )
                    git_branch = (
                        git_info.get("lastBuiltRevision", {})
                        .get("branch", [{}])[0]
                        .get("name", "unknown")
                    )
                    git_commit = git_info.get("lastBuiltRevision", {}).get(
                        "SHA1", "unknown"
                    )[:7]

                    result_emoji = {
                        "SUCCESS": "✅",
                        "FAILURE": "❌",
                        "UNSTABLE": "⚠️",
                        "ABORTED": "🚫",
                        "UNKNOWN": "❓",
                    }.get(result, "❓")

                    completion_message = (
                        f"📋 *Deployment Complete*\n"
                        f"• Build: {display_name}\n"
                        f"• Branch: {branch}\n"
                        f"• Environment: {environment}\n"
                        f"• Git Branch: {git_branch}\n"
                        f"• Commit: {git_commit}\n"
                        f"• Result: {result} {result_emoji}\n"
                        f"• Duration: {duration:.2f} seconds\n"
                        f"• Details: {JENKINS_URL}{build_number}/"
                    )

                    print("\nSending completion message...")
                    send_slack_message(channel_id, completion_message)
                    print("Final status message sent")
                    return

            attempt += 1
            time.sleep(check_interval)

        except Exception as e:
            print(f"\nERROR in monitoring: {str(e)}")
            print(f"Exception type: {type(e)}")
            error_message = (
                f"⚠️ *Deployment Monitor Error*\n"
                f"• Build: #{build_number}\n"
                f"• Error: {str(e)}"
            )
            send_slack_message(channel_id, error_message)
            return

    print("\n=== Monitor Timed Out ===")
    timeout_message = (
        f"⏰ *Deployment Monitor Timeout*\n"
        f"• Build: #{build_number}\n"
        f"• Status: Monitor timed out after {max_attempts * check_interval} seconds\n"
        f"• Details: {JENKINS_URL}{build_number}/"
    )
    send_slack_message(channel_id, timeout_message)


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
    channel_id = None  # Initialize channel_id at the start

    try:
        # Verify content type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415

        # Get request data
        request_data = request.get_json()
        if not request_data or "message" not in request_data:
            return jsonify({"error": "Missing 'message' in request body"}), 400

        message = request_data["message"]
        channel_id = request_data.get("channel_id")  # Optional Slack channel

        print(f"\n=== Processing Deployment Request ===")
        print(f"Message: {message}")
        print(f"Channel ID: {channel_id}")

        # Parse deployment intent
        deployment_params = parse_deployment_intent(message)
        if not deployment_params:
            error_msg = "❌ Could not understand deployment request"
            if channel_id:
                send_slack_message(channel_id, error_msg)
            return jsonify({"error": error_msg}), 400

        # Trigger Jenkins build with parsed parameters
        build_url = f"{JENKINS_URL}build"
        response = requests.post(
            build_url, auth=(JENKINS_USER, JENKINS_TOKEN), params=deployment_params
        )

        if response.status_code not in [201, 200]:
            error_msg = f"❌ Failed to trigger deployment: {response.status_code}"
            if channel_id:
                send_slack_message(channel_id, error_msg)
            return jsonify({"error": error_msg}), 500

        # Get build number and start monitoring
        build_number = get_last_build_number()
        if not build_number:
            error_msg = "❌ Could not determine build number"
            if channel_id:
                send_slack_message(channel_id, error_msg)
            return jsonify({"error": error_msg}), 500

        # Start monitoring in background thread if channel_id provided
        if channel_id:
            Thread(
                target=monitor_build_status,
                args=(
                    build_number,
                    channel_id,
                    deployment_params["branch"],
                    deployment_params["environment"],
                ),
                daemon=True,
            ).start()

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"🚀 Deployment started: Build #{build_number}",
                    "build_number": build_number,
                    "parameters": deployment_params,
                }
            ),
            200,
        )

    except Exception as e:
        error_msg = f"❌ Error processing deployment request: {str(e)}"
        print(f"Error: {str(e)}")
        print(f"Request data: {request.get_data()}")
        if channel_id:  # Now channel_id is always defined
            send_slack_message(channel_id, error_msg)
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
