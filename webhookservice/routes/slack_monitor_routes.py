from flask import request, jsonify
import re
import json
from datetime import datetime
from .slack_events_routes import slack_events_bp, logger, processed_events
from webhookservice.services.dify_service import parse_monitoring_intent, send_metrics_to_dify
from webhookservice.services.slack_service import send_slack_message, update_message
from webhookservice.services.prometheus_service import PrometheusService
from webhookservice.utils.metrics_formatter import format_metrics_message

prometheus_service = PrometheusService()

@slack_events_bp.route("/monitor/events", methods=["POST"])
def handle_monitor_events():
    """Handle Slack events for monitoring requests"""
    try:
        data = request.json
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge")}), 200
        event_id = data.get("event_id")
        if event_id:
            if event_id in processed_events:
                logger.info(f"Skipping duplicate event: {event_id}")
                return jsonify({"ok": True}), 200
            processed_events.add(event_id)
            if len(processed_events) > 1000:
                processed_events.clear()
        if data.get("event", {}).get("type") == "app_mention":
            event = data["event"]
            channel_id = event.get("channel")
            text = event.get("text")
            message = re.sub(r"<@[A-Za-z0-9]+>", "", text).strip()
            logger.info(f"Processing monitoring request: {message}")
            result = parse_monitoring_intent(message)
            if not result:
                logger.warning("Failed to parse monitoring intent")
                send_slack_message(
                    channel_id,
                    "❌ Sorry, I couldn't understand your request. Try asking for specific metrics like CPU usage, memory usage, or custom queries.",
                )
                return jsonify({"ok": True}), 200
            if "type" in result:
                if result["type"] == "help":
                    logger.info(f"Sending help message: {result['message']}")
                    send_slack_message(channel_id, result["message"])
                else:
                    logger.info(f"Received non-monitoring response: {result['message']}")
                    send_slack_message(channel_id, result["message"])
                return jsonify({"ok": True}), 200
            try:
                if result.get("query_type") == "current":
                    metric_name = result.get("metric")
                    metrics = prometheus_service.get_process_metrics(metric_name)
                    metrics["server_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                elif result.get("query_type") == "range":
                    logger.debug(f"Querying time series data with parameters: metric={result.get('metric')}, time_range={result.get('hours')} {result.get('unit', 'hours')}")
                    time_value = int(result.get("hours", 1))
                    time_unit = result.get("unit", "hours")
                    if time_unit == "minutes":
                        hours = time_value / 60
                    else:
                        hours = time_value
                    metrics = prometheus_service.get_metrics_range(
                        metric_name=result.get("metric", "todo_process_cpu_seconds_total"),
                        hours=hours,
                    )
                    logger.debug(f"Raw metrics response from Prometheus: {metrics}")
                else:
                    query = result.get("query", result.get("metric", ""))
                    metrics = prometheus_service.query(query)
                logger.debug("Sending metrics to Dify for analysis")
                dify_response = send_metrics_to_dify(metrics)
                logger.debug(f"Response from Dify: {dify_response}")
                raw_metrics = dify_response["raw_metrics"]
                logger.debug(f"Processing raw metrics for display: {raw_metrics}")
                
                formatted_message = format_metrics_message(raw_metrics, dify_response)
                send_slack_message(
                    channel_id,
                    "System Health Report",
                    blocks=formatted_message,
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
        channel_id = payload["channel"]["id"]
        message_ts = payload["message"]["ts"]
        logger.info(f"Processing monitoring action: {action_id}")
        if action_id == "refresh_metrics":
            try:
                metrics = prometheus_service.get_process_metrics()
                metrics["server_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                dify_response = send_metrics_to_dify(metrics)
                raw_metrics = dify_response["raw_metrics"]
                
                formatted_message = format_metrics_message(raw_metrics, dify_response, is_refresh=True)
                update_message(
                    channel_id,
                    message_ts,
                    formatted_message,
                    "System Health Report (Refreshed)",
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