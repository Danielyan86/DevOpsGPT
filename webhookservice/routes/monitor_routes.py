from flask import Blueprint, jsonify, request
from webhookservice.services.prometheus_service import PrometheusService
from webhookservice.utils.error_handler import handle_errors

monitor_bp = Blueprint("monitor", __name__)
prometheus_service = PrometheusService()


@monitor_bp.route("/metrics/current", methods=["GET"])
@handle_errors
def get_current_metrics():
    """Get current process metrics"""
    metrics = prometheus_service.get_process_metrics()
    return jsonify(metrics)


@monitor_bp.route("/metrics/range", methods=["GET"])
@handle_errors
def get_metrics_range():
    """Get metrics over a time range"""
    metric_name = request.args.get("metric", "todo_process_cpu_seconds_total")
    hours = int(request.args.get("hours", "1"))

    data = prometheus_service.get_metrics_range(metric_name, hours)
    return jsonify(data)


@monitor_bp.route("/metrics/query", methods=["GET"])
@handle_errors
def query_metrics():
    """Execute a custom Prometheus query"""
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    result = prometheus_service.query(query)
    return jsonify(result)
