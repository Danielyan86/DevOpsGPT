from flask import Blueprint, request, jsonify
import re
import json
from webhookservice.services.dify_service import parse_deployment_intent
from webhookservice.services.slack_service import (
    send_slack_message,
    send_interactive_message,
)
from webhookservice.services.jenkins_service import trigger_jenkins_build
from slack_sdk import WebClient
from config.settings import SLACK_BOT_TOKEN

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


@jenkins_bp.route("/deploy/actions", methods=["POST"])
def handle_slack_actions():
    """Handle interactive component actions from Slack"""
    try:
        payload = json.loads(request.form.get("payload"))
        action = payload["actions"][0]
        action_id = action["action_id"]

        # Get the original message timestamp and channel for updating
        channel_id = payload["channel"]["id"]
        message_ts = payload["message"]["ts"]
        client = WebClient(token=SLACK_BOT_TOKEN)

        if action_id == "confirm_deploy":
            deployment_params = json.loads(action["value"])
            response = trigger_jenkins_build(**deployment_params)

            if response.status_code in [201, 200]:
                # Update the original message to remove buttons
                client.chat_update(
                    channel=channel_id,
                    ts=message_ts,
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🚀 *Deployment Started*\n• Branch: `{deployment_params['branch']}`\n• Environment: `{deployment_params['environment']}`",
                            },
                        }
                    ],
                    text=f"Deployment started for {deployment_params['branch']}",
                )
                return jsonify({"ok": True})

            return jsonify(
                {"response_type": "in_channel", "text": "❌ Failed to start deployment"}
            )

        elif action_id == "cancel_deploy":
            # Update the original message to show cancellation
            client.chat_update(
                channel=channel_id,
                ts=message_ts,
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "❌ *Deployment Cancelled*"},
                    }
                ],
                text="Deployment cancelled",
            )
            return jsonify({"ok": True})

    except Exception as e:
        print(f"Error handling action: {str(e)}")
        return (
            jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"❌ Error processing action: {str(e)}",
                }
            ),
            500,
        )
