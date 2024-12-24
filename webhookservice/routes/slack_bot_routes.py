from flask import Blueprint, request, jsonify
import re
import json
import logging
from webhookservice.services.dify_service import (
    parse_deployment_intent,
    parse_monitoring_intent,
)
from webhookservice.services.slack_service import (
    send_slack_message,
    send_interactive_message,
    update_message,
)
from webhookservice.services.jenkins_service import trigger_jenkins_build, BuildResponse
from webhookservice.services.prometheus_service import PrometheusService
from datetime import datetime

logger = logging.getLogger(__name__)
slack_events_bp = Blueprint("slack_events", __name__)
prometheus_service = PrometheusService()

# Store processed event IDs to prevent duplicates
processed_events = set()


@slack_events_bp.route("/deploy/events", methods=["POST"])
def handle_deploy_events():
    """Handle Slack events for deployment requests"""
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
                send_slack_message(channel_id, result["message"], is_monitor=False)
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
                    is_monitor=False,
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
                    is_monitor=False,
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
                is_monitor=False,
            )
            return jsonify({"ok": True})

        return jsonify({"ok": True})

    except Exception as e:
        logger.error(f"Error handling action: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@slack_events_bp.route("/monitor/events", methods=["POST"])
def handle_monitor_events():
    """Handle Slack events for monitoring requests"""
    try:
        data = request.json

        # Handle Slack URL verification
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")}), 200

        # Check for duplicate events
        event_id = data.get("event_id")
        if event_id:
            if event_id in processed_events:
                logger.info(f"Skipping duplicate event: {event_id}")
                return jsonify({"ok": True}), 200
            processed_events.add(event_id)
            # Keep the set size manageable
            if len(processed_events) > 1000:
                processed_events.clear()

        # Process app_mention events
        if data.get("event", {}).get("type") == "app_mention":
            event = data["event"]
            channel_id = event.get("channel")
            text = event.get("text")

            # Remove the bot mention from the text
            message = re.sub(r"<@[A-Za-z0-9]+>", "", text).strip()
            logger.info(f"Processing monitoring request: {message}")

            # Parse monitoring intent using Dify
            result = parse_monitoring_intent(message)
            if not result:
                logger.warning("Failed to parse monitoring intent")
                send_slack_message(
                    channel_id,
                    "❌ Sorry, I couldn't understand your request. Try asking for specific metrics like CPU usage, memory usage, or custom queries.",
                )
                return jsonify({"ok": True}), 200

            # Check if this is a help or non-monitoring message
            if "type" in result:
                if result["type"] == "help":
                    logger.info(f"Sending help message: {result['message']}")
                    send_slack_message(channel_id, result["message"])
                else:
                    logger.info(
                        f"Received non-monitoring response: {result['message']}"
                    )
                    send_slack_message(channel_id, result["message"])
                return jsonify({"ok": True}), 200

            try:
                # Get metrics based on the query type
                if result.get("query_type") == "current":
                    metrics = prometheus_service.get_process_metrics()
                    # Add server time to metrics
                    metrics["server_time"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                elif result.get("query_type") == "range":
                    metrics = prometheus_service.get_metrics_range(
                        metric_name=result.get(
                            "metric_name", "todo_process_cpu_seconds_total"
                        ),
                        hours=int(result.get("time_range", 1)),
                    )
                else:  # custom query
                    query = result.get("query", result.get("metric_name", ""))
                    metrics = prometheus_service.query(query)

                # Format and send the response
                formatted_metrics = json.dumps(metrics, indent=2)
                send_slack_message(
                    channel_id,
                    f"�� *Monitoring Results*\n```{formatted_metrics}```",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"📊 *Monitoring Results*\n```{formatted_metrics}```",
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "🔄 Refresh",
                                        "emoji": True,
                                    },
                                    "action_id": "refresh_metrics",
                                }
                            ],
                        },
                    ],
                    is_monitor=True,
                )
                return jsonify({"ok": True}), 200

            except Exception as e:
                error_msg = f"Error fetching metrics: {str(e)}"
                logger.error(error_msg)
                send_slack_message(channel_id, f"❌ {error_msg}", is_monitor=True)
                return jsonify({"ok": True}), 200

        return jsonify({"ok": True}), 200

    except Exception as e:
        logger.error(f"Error handling monitor event: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@slack_events_bp.route("/monitor/actions", methods=["POST"])
def handle_monitor_actions():
    """Handle interactive component actions for monitoring"""
    try:
        payload = json.loads(request.form.get("payload"))
        action = payload["actions"][0]
        action_id = action["action_id"]

        # Get channel info from payload
        channel_id = payload["channel"]["id"]
        message_ts = payload["message"]["ts"]

        logger.info(f"Processing monitoring action: {action_id}")

        if action_id == "refresh_metrics":
            # Handle refresh metrics action
            try:
                metrics = prometheus_service.get_process_metrics()
                # Add server time to metrics
                metrics["server_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                formatted_metrics = json.dumps(metrics, indent=2)

                # Update the original message with new metrics
                update_message(
                    channel_id,
                    message_ts,
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"📊 *Updated Monitoring Results*\n```{formatted_metrics}```",
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "🔄 Refresh",
                                        "emoji": True,
                                    },
                                    "action_id": "refresh_metrics",
                                }
                            ],
                        },
                    ],
                    f"Updated metrics at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    is_monitor=True,
                )
                return jsonify({"ok": True})

            except Exception as e:
                error_msg = f"Error refreshing metrics: {str(e)}"
                logger.error(error_msg)
                update_message(
                    channel_id,
                    message_ts,
                    [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"❌ *Error*\n{error_msg}",
                            },
                        }
                    ],
                    error_msg,
                    is_monitor=True,
                )
                return jsonify({"ok": True})

        return jsonify({"ok": True})

    except Exception as e:
        logger.error(f"Error handling monitoring action: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
