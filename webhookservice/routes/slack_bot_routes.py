from flask import Blueprint, request, jsonify
import re
import json
import logging
from webhookservice.services.dify_service import parse_deployment_intent
from webhookservice.services.slack_service import (
    send_slack_message,
    send_interactive_message,
)
from webhookservice.services.jenkins_service import trigger_jenkins_build, BuildResponse
from slack_sdk import WebClient
from config.settings import SLACK_BOT_TOKEN

logger = logging.getLogger(__name__)
slack_events_bp = Blueprint("slack_events", __name__)


def update_message(channel_id: str, ts: str, blocks: list, text: str):
    """Helper function to update Slack messages"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        return client.chat_update(
            channel=channel_id,
            ts=ts,
            blocks=blocks,
            text=text,
            replace_original=True,
        )
    except Exception as e:
        logger.error(f"Error updating Slack message: {str(e)}")
        raise


@slack_events_bp.route("/deploy/events", methods=["POST"])
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
            logger.info(f"Processing deployment request: {message}")

            # Parse deployment intent using Dify
            result = parse_deployment_intent(message)
            if not result:
                logger.warning("Failed to parse deployment intent")
                send_slack_message(
                    channel_id,
                    "❌ Sorry, I couldn't understand your deployment request.",
                )
                return jsonify({"ok": True}), 200

            # Check if this is a non-deployment message
            if "message" in result:
                logger.info(f"Received non-deployment response: {result['message']}")
                send_slack_message(channel_id, result["message"])
                return jsonify({"ok": True}), 200

            # Continue with deployment confirmation
            logger.info(f"Parsed deployment parameters: {result}")

            # Create confirmation message with interactive buttons
            confirmation_message = {
                "channel": channel_id,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Deployment Confirmation*\nDo you want to deploy with these parameters?\n• Branch: `{result['branch']}`\n• Environment: `{result['environment']}`",
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
                                "value": json.dumps(result),
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

            send_interactive_message(
                channel_id,
                confirmation_message["blocks"],
                fallback_text=f"Deployment confirmation request for branch {result['branch']} to {result['environment']}",
            )
            return jsonify({"ok": True}), 200

        return jsonify({"ok": True}), 200

    except Exception as e:
        logger.error(f"Error handling Slack event: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@slack_events_bp.route("/deploy/actions", methods=["POST"])
def handle_slack_actions():
    """Handle interactive component actions from Slack"""
    try:
        payload = json.loads(request.form.get("payload"))
        action = payload["actions"][0]
        action_id = action["action_id"]

        # Get channel info from payload
        channel_id = payload["channel"]["id"]
        message_ts = payload["message"]["ts"]
        # Get channel name from the payload or API
        channel_name = f"#{payload['channel']['name']}"

        logger.info(f"Processing action: {action_id} for channel: {channel_name}")

        if action_id == "confirm_deploy":
            deployment_params = json.loads(action["value"])
            # Add the actual channel to deployment parameters
            deployment_params.update({"channel": channel_name})

            logger.info(f"Deployment Parameters: {deployment_params}")

            response = trigger_jenkins_build(**deployment_params)
            logger.info(f"Jenkins build response: {response}")

            if response.success:
                # Update the original message to remove buttons
                update_message(
                    channel_id,
                    message_ts,
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"🚀 *Deployment Started*\n• Branch: `{deployment_params['branch']}`\n• Environment: `{deployment_params['environment']}`",
                            },
                        }
                    ],
                    f"Deployment started for {deployment_params['branch']}",
                )
                return jsonify({"ok": True})
            else:
                logger.error(f"Deployment failed: {response.message}")
                # Update the original message to show error
                update_message(
                    channel_id,
                    message_ts,
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"❌ *Deployment Failed*\n• Error: {response.message}\n• Branch: `{deployment_params['branch']}`\n• Environment: `{deployment_params['environment']}`",
                            },
                        }
                    ],
                    f"Deployment failed: {response.message}",
                )
                return jsonify({"ok": True})

        elif action_id == "cancel_deploy":
            # Update the original message to show cancellation
            update_message(
                channel_id,
                message_ts,
                [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "❌ *Deployment Cancelled*"},
                    }
                ],
                "Deployment cancelled",
            )
            return jsonify({"ok": True})

    except Exception as e:
        logger.error(f"Error handling action: {str(e)}", exc_info=True)
        return (
            jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"❌ Error processing action: {str(e)}",
                }
            ),
            500,
        )
