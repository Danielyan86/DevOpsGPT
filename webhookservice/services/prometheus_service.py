import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class PrometheusService:
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1"

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

    def get_process_metrics(self) -> Dict[str, Any]:
        """
        Get basic process metrics for the application
        """
        metrics = {}

        # CPU Usage
        cpu_query = "todo_process_cpu_seconds_total"
        cpu_result = self.query(cpu_query)
        if cpu_result["data"]["result"]:
            metrics["cpu_usage"] = float(cpu_result["data"]["result"][0]["value"][1])

        # Memory Usage
        memory_query = "todo_process_resident_memory_bytes"
        memory_result = self.query(memory_query)
        if memory_result["data"]["result"]:
            metrics["memory_usage"] = float(
                memory_result["data"]["result"][0]["value"][1]
            )

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
