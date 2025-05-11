from flask import Blueprint, jsonify, request
from webhookservice.services.prometheus_service import PrometheusService
from webhookservice.utils.error_handler import handle_errors
from webhookservice.services.dify_service import parse_monitoring_intent
from webhookservice.services.slack_service import send_slack_message
import json

prometheus_bp = Blueprint("prometheus", __name__)
prometheus_service = PrometheusService()


@prometheus_bp.route("/metrics/current", methods=["GET"])
@handle_errors
def get_current_metrics():
    """Get current process metrics"""
    metrics = prometheus_service.get_process_metrics()
    return jsonify(metrics)


@prometheus_bp.route("/metrics/range", methods=["GET"])
@handle_errors
def get_metrics_range():
    """Get metrics over a time range"""
    metric_name = request.args.get("metric", "todo_process_cpu_seconds_total")
    hours = int(request.args.get("hours", "1"))

    data = prometheus_service.get_metrics_range(metric_name, hours)
    return jsonify(data)


@prometheus_bp.route("/metrics/query", methods=["GET"])
@handle_errors
def query_metrics():
    """Execute a custom Prometheus query"""
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    result = prometheus_service.query(query)
    return jsonify(result)


@prometheus_bp.route("/monitor-chat", methods=["POST"])
@handle_errors
def handle_natural_language_monitor():
    """Handle natural language monitoring requests from Slack"""
    try:
        content_type = request.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            request_data = request.get_json()
        elif "application/x-www-form-urlencoded" in content_type:
            request_data = {
                "message": request.form.get("text", request.form.get("message")),
                "channel_id": request.form.get("channel_id"),
            }
        else:
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
            return jsonify({"error": "Missing 'message' or 'text' in request"}), 400

        # Parse the monitoring intent using Dify
        monitoring_params = parse_monitoring_intent(request_data["message"])
        if not monitoring_params:
            return jsonify({"error": "Could not understand monitoring request"}), 400

        # If it's a non-monitoring message, return the message
        if "message" in monitoring_params:
            return jsonify({"message": monitoring_params["message"]}), 200

        # Get the metrics based on the query type
        if monitoring_params.get("query_type") == "current":
            result = prometheus_service.get_process_metrics()
        elif monitoring_params.get("query_type") == "range":
            result = prometheus_service.get_metrics_range(
                metric_name=monitoring_params.get(
                    "metric_name", "todo_process_cpu_seconds_total"
                ),
                hours=int(monitoring_params.get("time_range", 1)),
            )
        else:  # custom query
            result = prometheus_service.query(monitoring_params.get("query", ""))

        # Format the response for Slack
        if request_data.get("channel_id"):
            formatted_result = json.dumps(result, indent=2)
            send_slack_message(
                request_data["channel_id"],
                f"📊 *Monitoring Results*\n```{formatted_result}```",
            )

        return (
            jsonify(
                {"message": "Monitoring results retrieved successfully", "data": result}
            ),
            200,
        )

    except Exception as e:
        error_msg = f"Error processing monitoring request: {str(e)}"
        if request_data.get("channel_id"):
            send_slack_message(request_data["channel_id"], f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500


@prometheus_bp.route("/test-dify", methods=["POST"])
@handle_errors
def test_dify_intent():
    """Test endpoint for Dify intent parsing"""
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415

        data = request.get_json()
        message = data.get("message")

        if not message:
            return jsonify({"error": "Missing 'message' in request"}), 400

        # Parse the monitoring intent using Dify
        result = parse_monitoring_intent(message)

        return jsonify({"input_message": message, "parsed_result": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500 