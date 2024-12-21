from flask import Blueprint, request, jsonify
import re
import json
from webhookservice.services.dify_service import parse_deployment_intent
from webhookservice.services.slack_service import (
    send_slack_message,
    send_interactive_message,
)

jenkins_bp = Blueprint("slack_events", __name__)


@jenkins_bp.route("/deploy/events", methods=["POST"])
def handle_slack_events():
    """Handle Slack events, specifically app_mention events"""
    try:
        data = request.json

        # Handle Slack URL verification
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")}), 200

        # Process app_mention events
        if data.get("event", {}).get("type") == "app_mention":
            event = data["event"]
            channel_id = event.get("channel")
            text = event.get("text")

            # Remove the bot mention from the text
            # e.g., "<@U1234> deploy to prod" -> "deploy to prod"
            message = re.sub(r"<@[A-Za-z0-9]+>", "", text).strip()

            # Parse deployment intent using Dify
            deployment_params = parse_deployment_intent(message)
            if not deployment_params:
                send_slack_message(
                    channel_id,
                    "❌ Sorry, I couldn't understand your deployment request.",
                )
                return jsonify({"ok": True}), 200

            # Create confirmation message with interactive buttons
            confirmation_message = {
                "channel": channel_id,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Deployment Confirmation*\nDo you want to deploy with these parameters?\n• Branch: `{deployment_params['branch']}`\n• Environment: `{deployment_params['environment']}`",
                        },
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Confirm Deploy",
                                    "emoji": True,
                                },
                                "style": "primary",
                                "value": json.dumps(deployment_params),
                                "action_id": "confirm_deploy",
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Cancel",
                                    "emoji": True,
                                },
                                "style": "danger",
                                "value": "cancel",
                                "action_id": "cancel_deploy",
                            },
                        ],
                    },
                ],
            }

            send_interactive_message(channel_id, confirmation_message["blocks"])
            return jsonify({"ok": True}), 200

        return jsonify({"ok": True}), 200

    except Exception as e:
        print(f"Error handling Slack event: {str(e)}")
        return jsonify({"error": str(e)}), 500
