from flask import Blueprint, request, jsonify
from threading import Thread
from webhookservice.services.jenkins_service import (
    trigger_jenkins_build,
    get_last_build_number,
    monitor_build_status,
)
from webhookservice.services.slack_service import send_slack_message
from webhookservice.services.dify_service import parse_deployment_intent

jenkins_bp = Blueprint("jenkins", __name__)


@jenkins_bp.route("/deploy-command", methods=["POST"])
def handle_slack_command():
    user_input = request.form.get("text")
    channel_id = request.form.get("channel_id")

    params = dict(item.split("=") for item in user_input.split())
    branch = params.get("branch", "main")
    environment = params.get("environment", "staging")

    try:
        response = trigger_jenkins_build(branch, environment)

        if response.status_code in [201, 200]:
            build_number = get_last_build_number()
            if build_number:
                Thread(
                    target=monitor_build_status,
                    args=(build_number, channel_id, branch, environment),
                    daemon=True,
                ).start()

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
                f"❌ Failed to trigger Jenkins Job. Status: {response.status_code}"
            )
            send_slack_message(channel_id, error_msg)
            return jsonify({"response_type": "in_channel", "text": error_msg}), 500

    except Exception as e:
        error_msg = f"❌ Error calling Jenkins: {str(e)}"
        send_slack_message(channel_id, error_msg)
        return jsonify({"response_type": "in_channel", "text": error_msg}), 500


@jenkins_bp.route("/deploy-chat", methods=["POST"])
def handle_natural_language_deploy():
    """Handle natural language deployment requests"""
    try:
        print("\n" + "=" * 50)
        print("=== INCOMING REQUEST ===")
        content_type = request.headers.get("Content-Type", "").lower()
        print(f"Content-Type: {content_type}")

        if "application/json" in content_type:
            request_data = request.get_json()
        elif "application/x-www-form-urlencoded" in content_type:
            request_data = {
                "message": request.form.get("text", request.form.get("message")),
                "channel_id": request.form.get("channel_id"),
            }
        else:
            print("=== ERROR: Invalid Content-Type ===")
            return (
                jsonify(
                    {
                        "error": "Content-Type must be application/json or application/x-www-form-urlencoded",
                        "received": content_type,
                    }
                ),
                415,
            )

        if not request_data or not request_data.get("message"):
            print("=== ERROR: Missing Message ===")
            return jsonify({"error": "Missing 'message' or 'text' in request"}), 400

        print("\n" + "=" * 50)
        print("=== DIFY API REQUEST ===")
        print(f"Message: {request_data['message']}")

        deployment_params = parse_deployment_intent(request_data["message"])
        if not deployment_params:
            print("=== ERROR: Could not parse deployment intent ===")
            return jsonify({"error": "Could not understand deployment request"}), 400

        print("\n" + "=" * 50)
        print("=== JENKINS BUILD REQUEST ===")
        print(f"Parameters: {deployment_params}")

        response = trigger_jenkins_build(**deployment_params)

        if response.status_code not in [201, 200]:
            print(f"=== ERROR: Jenkins Build Failed ({response.status_code}) ===")
            return (
                jsonify(
                    {
                        "error": f"Failed to trigger Jenkins build: {response.status_code}"
                    }
                ),
                500,
            )

        print("\n" + "=" * 50)
        print("=== SUCCESS: Build Triggered ===")
        return (
            jsonify(
                {
                    "message": ":rocket: Deployment triggered successfully",
                    "parameters": deployment_params,
                    "status": ":white_check_mark: Pipeline started",
                }
            ),
            200,
        )

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"=== ERROR: Unexpected Exception ===")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        return jsonify({"error": f"Error processing deployment request: {str(e)}"}), 500
