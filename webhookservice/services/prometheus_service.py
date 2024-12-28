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

        logger = logging.getLogger(__name__)
        logger.debug(
            f"Querying Prometheus - URL: {self.api_url}/query, Params: {params}"
        )

        response = requests.get(f"{self.api_url}/query", params=params)
        logger.debug(f"Prometheus response status: {response.status_code}")
        logger.debug(f"Prometheus response: {response.text}")

        response.raise_for_status()
        return response.json()

    def query_range(
        self, query: str, start: str, end: str, step: str
    ) -> Dict[str, Any]:
        """
        Execute a query over a range of time
        """
        logger = logging.getLogger(__name__)
        params = {"query": query, "start": start, "end": end, "step": step}
        logger.debug(
            f"Querying Prometheus range - URL: {self.api_url}/query_range, Params: {params}"
        )

        response = requests.get(f"{self.api_url}/query_range", params=params)
        logger.debug(f"Prometheus range query response status: {response.status_code}")
        logger.debug(f"Prometheus range query response: {response.text}")

        response.raise_for_status()
        return response.json()

    def get_process_metrics(self, metric_name: str = None) -> Dict[str, Any]:
        """
        Get basic process metrics for the application

        Args:
            metric_name: Optional specific metric to query
                        Use 'all' to get all metrics

        Returns:
            Dict[str, Any]: The requested metrics
        """
        metrics = {}
        logger = logging.getLogger(__name__)
        logger.debug(f"Getting process metrics for: {metric_name}")

        try:
            # Map common metric names to actual Prometheus metrics
            metric_mapping = {
                "cpu": "todo_process_cpu_seconds_total",
                "memory": "todo_process_resident_memory_bytes",
                "todo_process_cpu_seconds_total": "todo_process_cpu_seconds_total",
                "todo_process_resident_memory_bytes": "todo_process_resident_memory_bytes",
            }
            logger.debug(f"Metric mapping: {metric_mapping}")

            # If metric_name is 'all', 'up', None, or not in our mapping, query all metrics
            if (
                not metric_name
                or metric_name.lower() in ["all", "up"]
                or metric_name.lower() not in metric_mapping
            ):
                logger.debug("Querying all metrics")

                # CPU Usage
                logger.debug("Querying CPU metric")
                cpu_query = f'rate({metric_mapping["cpu"]}[1m]) * 100'  # Calculate rate over 1 minute and convert to percentage
                cpu_result = self.query(cpu_query)
                logger.debug(f"CPU query result: {cpu_result}")

                if cpu_result["data"]["result"]:
                    cpu_value = float(cpu_result["data"]["result"][0]["value"][1])
                    metrics["cpu_usage"] = cpu_value
                    logger.debug(f"CPU usage: {cpu_value}%")
                else:
                    logger.debug("No CPU data found in response")

                # Memory Usage
                logger.debug("Querying Memory metric")
                memory_result = self.query(metric_mapping["memory"])
                logger.debug(f"Memory query result: {memory_result}")

                if memory_result["data"]["result"]:
                    memory_value = float(memory_result["data"]["result"][0]["value"][1])
                    metrics["memory_usage"] = memory_value
                    logger.debug(f"Memory usage: {memory_value} bytes")
                else:
                    logger.debug("No memory data found in response")

            else:
                logger.debug(f"Querying specific metric: {metric_name}")
                # Convert common names to actual metrics
                actual_metric = metric_mapping.get(metric_name.lower())
                logger.debug(f"Resolved metric name: {actual_metric}")

                if actual_metric:
                    if "cpu" in actual_metric.lower():
                        query = f"rate({actual_metric}[1m]) * 100"  # Calculate rate over 1 minute and convert to percentage
                    else:
                        query = actual_metric

                    result = self.query(query)
                    logger.debug(f"Query result for {actual_metric}: {result}")

                    if result["data"]["result"]:
                        value = float(result["data"]["result"][0]["value"][1])
                        if "cpu" in actual_metric.lower():
                            metrics["cpu_usage"] = (
                                value  # Value is already a percentage
                            )
                            logger.debug(f"CPU usage: {value}%")
                        elif "memory" in actual_metric.lower():
                            metrics["memory_usage"] = value
                            logger.debug(f"Memory usage: {value} bytes")
                    else:
                        logger.debug(f"No data found for metric: {actual_metric}")

            logger.debug(f"Final metrics: {metrics}")
            return metrics

        except Exception as e:
            logger.error(f"Error getting process metrics: {str(e)}", exc_info=True)
            return metrics

    def get_metrics_range(self, metric_name: str, hours: float = 1.0) -> Dict[str, Any]:
        """
        Get metric values over a time range

        Args:
            metric_name: The name of the metric to query
            hours: Number of hours to look back (can be fractional for minutes)
        """
        logger = logging.getLogger(__name__)
        logger.debug(f"Getting metrics range for {metric_name} over {hours} hours")

        end = datetime.now()
        start = end - timedelta(hours=hours)
        logger.debug(f"Time range: start={start.isoformat()}, end={end.isoformat()}")

        # Adjust step size based on time range
        if hours <= 1:  # For ranges up to 1 hour
            step = "15s"  # Use 15-second intervals
        elif hours <= 6:  # For ranges up to 6 hours
            step = "1m"  # Use 1-minute intervals
        else:
            step = "5m"  # Use 5-minute intervals for longer ranges

        logger.debug(f"Using step size: {step}")

        # If it's a CPU metric, use rate function
        if "cpu" in metric_name.lower():
            query = f"rate({metric_name}[1m]) * 100"
        else:
            query = metric_name
        logger.debug(f"Prometheus query: {query}")

        result = self.query_range(
            query=query,
            start=start.isoformat("T") + "Z",
            end=end.isoformat("T") + "Z",
            step=step,
        )
        logger.debug(f"Raw query_range result: {result}")

        # Convert timestamps in the response
        if result.get("data", {}).get("result"):
            logger.debug("Processing time series data")
            for series in result["data"]["result"]:
                if "values" in series:
                    for value in series["values"]:
                        # Convert timestamp to datetime
                        timestamp = datetime.fromtimestamp(value[0])
                        value[0] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"Processed result: {result}")
        else:
            logger.debug("No time series data found in the response")

        return result
