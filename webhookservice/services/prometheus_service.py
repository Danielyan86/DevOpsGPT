import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from config.settings import PROMETHEUS_BASE_URL
import logging


class PrometheusService:
    def __init__(self):
        self.base_url = PROMETHEUS_BASE_URL
        self.api_url = f"{self.base_url}/api/v1"

    def query(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute an instant query at a single point in time
        """
        params = {"query": query}
        if time:
            params["time"] = time

        response = requests.get(f"{self.api_url}/query", params=params)
        response.raise_for_status()
        return response.json()

    def query_range(
        self, query: str, start: str, end: str, step: str
    ) -> Dict[str, Any]:
        """
        Execute a query over a range of time
        """
        params = {"query": query, "start": start, "end": end, "step": step}

        response = requests.get(f"{self.api_url}/query_range", params=params)
        response.raise_for_status()
        return response.json()

    def get_process_metrics(self, metric_name: str = None) -> Dict[str, Any]:
        """
        Get basic process metrics for the application

        Args:
            metric_name: Optional specific metric to query (e.g., 'todo_process_cpu_seconds_total' or 'todo_process_resident_memory_bytes')
                        Use 'all' to get all metrics

        Returns:
            Dict[str, Any]: The requested metrics
        """
        metrics = {}
        logger = logging.getLogger(__name__)

        try:
            # Map common metric names to actual Prometheus metrics
            metric_mapping = {
                "cpu": "todo_process_cpu_seconds_total",
                "memory": "todo_process_resident_memory_bytes",
                "todo_process_cpu_seconds_total": "todo_process_cpu_seconds_total",
                "todo_process_resident_memory_bytes": "todo_process_resident_memory_bytes",
            }

            # If metric_name is 'all' or None, query all metrics
            if not metric_name or metric_name.lower() == "all":
                # CPU Usage
                cpu_result = self.query(metric_mapping["cpu"])
                if cpu_result["data"]["result"]:
                    metrics["cpu_usage"] = float(
                        cpu_result["data"]["result"][0]["value"][1]
                    )

                # Memory Usage
                memory_result = self.query(metric_mapping["memory"])
                if memory_result["data"]["result"]:
                    metrics["memory_usage"] = float(
                        memory_result["data"]["result"][0]["value"][1]
                    )
            else:
                # Convert common names to actual metrics
                actual_metric = None
                if metric_name.lower() in metric_mapping:
                    actual_metric = metric_mapping[metric_name.lower()]
                elif any(name in metric_name.lower() for name in ["cpu", "memory"]):
                    for key, value in metric_mapping.items():
                        if key in metric_name.lower():
                            actual_metric = value
                            break

                if actual_metric:
                    result = self.query(actual_metric)
                    if result["data"]["result"]:
                        value = float(result["data"]["result"][0]["value"][1])
                        if "cpu" in actual_metric.lower():
                            metrics["cpu_usage"] = value
                        elif "memory" in actual_metric.lower():
                            metrics["memory_usage"] = value

            return metrics

        except Exception as e:
            logger.error(f"Error getting process metrics: {str(e)}")
            return metrics

    def get_metrics_range(self, metric_name: str, hours: int = 1) -> Dict[str, Any]:
        """
        Get metric values over a time range
        """
        end = datetime.now()
        start = end - timedelta(hours=hours)

        query = f"{metric_name}"
        return self.query_range(
            query=query,
            start=start.isoformat("T") + "Z",
            end=end.isoformat("T") + "Z",
            step="5m",
        )
