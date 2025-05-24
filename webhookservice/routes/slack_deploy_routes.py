from flask import request, jsonify
import re
import json
from .slack_events_routes import slack_events_bp, logger, processed_events
from webhookservice.services.dify_service import parse_deployment_intent
from webhookservice.services.slack_service import send_slack_message, send_interactive_message, update_message

@slack_events_bp.route("/deploy/events", methods=["POST"])
def handle_deploy_events():
    """Handle Slack events for deployment requests"""
    try:
        data = request.json
        # Handle Slack URL verification
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")}), 200
        # Check for duplicate events
        event_id = data.get("event_id")
        if event_id:
            if event_id in processed_events:
                logger.info(f"Skipping duplicate deployment event: {event_id}")
                return jsonify({"ok": True}), 200
            processed_events.add(event_id)
            if len(processed_events) > 1000:
                processed_events.clear()
        # Process app_mention events
        if data.get("event", {}).get("type") == "app_mention":
            event = data["event"]
            channel_id = event.get("channel")
            text = event.get("text")
            message = re.sub(r"<@[A-Za-z0-9]+>", "", text).strip()
            logger.info(f"Processing deployment request: {message}")
            result = parse_deployment_intent(message)
            if not result:
                logger.warning("Failed to parse deployment intent")
                send_slack_message(
                    channel_id,
                    "❌ Sorry, I couldn't understand your deployment request.",
                )
                return jsonify({"ok": True}), 200
            if "message" in result:
                logger.info(f"Received non-deployment response: {result['message']}")
                send_slack_message(channel_id, result["message"], is_monitor=False)
                return jsonify({"ok": True}), 200
            logger.info(f"Parsed deployment parameters: {result}")
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
                is_monitor=False,
            )
            return jsonify({"ok": True}), 200
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.error(f"Error handling Slack event: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@slack_events_bp.route("/deploy/actions", methods=["POST"])
def handle_deploy_actions():
    """Handle interactive component actions for deployment"""
    try:
        payload = json.loads(request.form.get("payload"))
        action = payload["actions"][0]
        action_id = action["action_id"]
        channel_id = payload["channel"]["id"]
        message_ts = payload["message"]["ts"]
        channel_name = f"#{payload['channel']['name']}"
        logger.info(f"Processing action: {action_id} for channel: {channel_name}")
        if action_id == "confirm_deploy":
            deployment_params = json.loads(action["value"])
            deployment_params.update({"channel": channel_name})
            logger.info(f"Deployment Parameters: {deployment_params}")
            from webhookservice.services.jenkins_service import trigger_jenkins_build
            response = trigger_jenkins_build(**deployment_params)
            logger.info(f"Jenkins build response: {response}")
            if response.success:
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
                    is_monitor=False,
                )
                return jsonify({"ok": True})
            else:
                logger.error(f"Deployment failed: {response.message}")
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
                    is_monitor=False,
                )
                return jsonify({"ok": True})
        elif action_id == "cancel_deploy":
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
                is_monitor=False,
            )
            return jsonify({"ok": True})
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Error handling action: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500 