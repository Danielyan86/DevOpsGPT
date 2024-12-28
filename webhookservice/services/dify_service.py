import json
import requests
import logging
from typing import Dict, Optional, Any
from config.settings import (
    DIFY_DEPLOY_BOT_API_KEY,
    DIFY_MONITOR_BOT_API_KEY,
    DIFY_API_ENDPOINT,
)

logger = logging.getLogger(__name__)


def parse_deployment_intent(message: str) -> Optional[Dict]:
    """Parse deployment intent from natural language using Dify API"""
    try:
        logger.info(f"Processing deployment request: {message}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DIFY_DEPLOY_BOT_API_KEY}",
        }

        payload = json.dumps(
            {
                "inputs": {},
                "query": message,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "chatops-user",
                "files": [],
            }
        )

        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"Error response from Dify API: {response.text}")
            return {"error": response.text}

        thought_content = None
        message_content = None

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")

            # Handle ping events
            if line.startswith("event: ping"):
                continue

            # Remove "data: " prefix if present
            if line.startswith("data: "):
                line = line.replace("data: ", "")

            try:
                data = json.loads(line)
                event_type = data.get("event")

                if event_type == "agent_thought":
                    thought_content = data.get("thought", "")
                    if thought_content:
                        try:
                            thought_json = json.loads(thought_content)
                            if (
                                "branch" in thought_json
                                or "environment" in thought_json
                            ):
                                parsed_params = {
                                    "branch": thought_json.get("branch", "main"),
                                    "environment": thought_json.get(
                                        "environment", "staging"
                                    ),
                                }
                                logger.info(f"Deployment parameters: {parsed_params}")
                                return parsed_params
                        except json.JSONDecodeError:
                            continue

                elif event_type == "agent_message":
                    answer = data.get("answer", "").strip()
                    if answer and answer != "\n":
                        try:
                            answer_json = json.loads(answer)
                            if "branch" in answer_json or "environment" in answer_json:
                                parsed_params = {
                                    "branch": answer_json.get("branch", "main"),
                                    "environment": answer_json.get(
                                        "environment", "staging"
                                    ),
                                }
                                logger.info(f"Deployment parameters: {parsed_params}")
                                return parsed_params
                        except json.JSONDecodeError:
                            if not message_content or message_content.isspace():
                                message_content = answer

            except json.JSONDecodeError:
                continue

        if message_content and not message_content.isspace():
            return {"message": message_content}

        return None

    except requests.Timeout:
        logger.error("Request to Dify API timed out after 30 seconds")
        return {"error": "Request timed out"}
    except Exception as e:
        logger.error(f"Error in parse_deployment_intent: {str(e)}", exc_info=True)
        return None


def parse_monitoring_intent(message: str) -> Dict[str, Any]:
    """
    Parse monitoring requests using Dify API
    Returns a dictionary containing:
    - metric: The name of the metric to query
    - hours: Time range for the query (in hours)
    - query_type: 'current', 'range', or 'custom'
    Or for non-monitoring queries:
    - type: 'help' or other type
    - message: The response message
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DIFY_MONITOR_BOT_API_KEY}",
        }

        payload = json.dumps(
            {
                "inputs": {},
                "query": message,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "chatops-user",
                "files": [],
            }
        )

        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,
        )

        if response.status_code != 200:
            logger.error(f"Error from Dify API: {response.text}")
            return {"error": response.text}

        thought_content = None

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8").replace("data: ", "")
                try:
                    data = json.loads(line_str)
                    if data.get("event") == "agent_thought":
                        thought_content = data.get("thought", "")
                        if thought_content:
                            try:
                                thought_json = json.loads(thought_content)

                                # Check if this is a help or non-monitoring message
                                if (
                                    "type" in thought_json
                                    and thought_json["type"] == "help"
                                ):
                                    return thought_json

                                # Parse monitoring parameters
                                if "query_type" in thought_json:
                                    parsed_params = {
                                        "query_type": thought_json.get(
                                            "query_type", "current"
                                        ),
                                        "metric": thought_json.get("metric", "all"),
                                        "hours": int(thought_json.get("hours", 1)),
                                    }
                                    return parsed_params

                                # If we got JSON but it's not in the expected format
                                return {"type": "unknown", "message": str(thought_json)}

                            except json.JSONDecodeError:
                                # Return the raw thought content for non-JSON responses
                                return {"type": "text", "message": thought_content}
                except json.JSONDecodeError:
                    continue

        return None

    except Exception as e:
        logger.error(f"Error in parse_monitoring_intent: {str(e)}")
        return None


def send_metrics_to_dify(metrics: dict) -> dict:
    """
    Send monitoring metrics to Dify's MonitorBot API for analysis

    Args:
        metrics (dict): The metrics data from Prometheus

    Returns:
        dict: The analyzed response from Dify's MonitorBot
    """
    try:
        # Handle range query results
        if metrics.get("data", {}).get("resultType") == "matrix" and metrics.get(
            "data", {}
        ).get("result"):
            # Convert the range data to a more readable format
            series = metrics["data"]["result"][0]
            metric_name = series["metric"].get("__name__", "unknown")
            values = series["values"]

            # Format the data for analysis
            formatted_metrics = {
                "metric_name": metric_name,
                "values": [
                    {
                        "timestamp": value[0],
                        "value": (
                            float(value[1]) / 1024 / 1024
                            if "bytes" in metric_name.lower()
                            else float(value[1])
                        ),
                    }
                    for value in values
                ],
            }
            metrics_json = json.dumps(formatted_metrics)
            query = f"Please analyze these monitoring metrics over time and provide insights: {metrics_json}"
        else:
            # Handle instant query results (current metrics)
            metrics_json = json.dumps(metrics)
            query = f"Please analyze these monitoring metrics and provide insights: {metrics_json}"

        # Prepare the request to Dify's MonitorBot API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DIFY_MONITOR_BOT_API_KEY}",
        }

        payload = json.dumps(
            {
                "inputs": {},
                "query": query,
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "chatops-user",
                "files": [],
            }
        )

        # Send request to Dify API
        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,
        )

        if response.status_code != 200:
            logger.error(f"Error from Dify API: {response.text}")
            return {
                "analysis": f"Error from Dify API: {response.text}",
                "raw_metrics": metrics,
            }

        # Process streaming response
        analysis = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8").replace("data: ", "")
                try:
                    data = json.loads(line_str)
                    if data.get("event") == "message":
                        current = data.get("answer", "")
                        if current:
                            analysis.append(current)
                    elif data.get("event") == "agent_thought":
                        thought = data.get("thought", "")
                        if thought:
                            analysis.append(thought)
                    elif data.get("event") == "end":
                        final_answer = data.get("answer", "")
                        if final_answer:
                            analysis.append(final_answer)
                except json.JSONDecodeError:
                    continue

        # Join all analysis parts with newlines
        final_analysis = "\n".join(analysis) if analysis else "No analysis available"

        return {
            "analysis": final_analysis,
            "raw_metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Error sending metrics to Dify: {str(e)}")
        return {
            "analysis": f"Error analyzing metrics: {str(e)}",
            "raw_metrics": metrics,
        }
