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

        message_content = []
        complete_message = None

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
                            if thought_json:
                                complete_message = thought_json
                        except json.JSONDecodeError:
                            pass

                elif event_type == "agent_message":
                    answer = data.get("answer", "").strip()
                    if answer:
                        message_content.append(answer)

                elif event_type == "message_end":
                    # Try to parse the complete message
                    if message_content:
                        complete_text = "".join(message_content)
                        try:
                            complete_message = json.loads(complete_text)
                        except json.JSONDecodeError:
                            complete_message = {"message": complete_text}

            except json.JSONDecodeError:
                continue

        # Process the complete message
        if complete_message:
            if isinstance(complete_message, dict):
                if "type" in complete_message and complete_message["type"] == "help":
                    # Format help message for better readability
                    help_data = complete_message.get("message", {})
                    description = help_data.get("description", "")
                    # Add spaces to description
                    description = description.replace("Icanhelpyou", "I can help you")
                    description = description.replace(
                        "deployapplicationsto", "deploy applications to"
                    )
                    description = description.replace(
                        "differentenvironments", "different environments"
                    )
                    supported_commands = help_data.get("supported_commands", {})
                    examples = help_data.get("examples", [])

                    # Format examples with proper spacing
                    formatted_examples = []
                    for example in examples:
                        # Add spaces between words
                        formatted_example = example
                        # Handle deployment commands
                        formatted_example = formatted_example.replace(
                            "deploy", "deploy "
                        )
                        formatted_example = formatted_example.replace("test", "test ")
                        formatted_example = formatted_example.replace(
                            "toproduction", "to production"
                        )
                        # Handle update commands - do this first before other replacements
                        formatted_example = formatted_example.replace(
                            "updatestaging", "update staging"
                        )
                        formatted_example = formatted_example.replace(
                            "environment", " environment"
                        )
                        formatted_examples.append(formatted_example.strip())

                    formatted_message = [description, ""]

                    if supported_commands:
                        formatted_message.append("Supported commands:")
                        for category, commands in supported_commands.items():
                            formatted_message.append(
                                f"• {category.title()}: {', '.join(commands)}"
                            )
                        formatted_message.append("")

                    if formatted_examples:
                        formatted_message.append("Examples:")
                        for example in formatted_examples:
                            formatted_message.append(f"• {example}")

                    help_message = "\n".join(formatted_message)
                    logger.info(f"Returning help message: {help_message}")
                    return {"message": help_message}

                elif "branch" in complete_message or "environment" in complete_message:
                    parsed_params = {
                        "branch": complete_message.get("branch", "main"),
                        "environment": complete_message.get("environment", "staging"),
                    }
                    logger.info(f"Returning deployment parameters: {parsed_params}")
                    return parsed_params
                else:
                    # Return any other structured message
                    return {"message": str(complete_message)}
            else:
                # If not a dict, return as plain message
                return {"message": str(complete_message)}

        # If we get here and have message content but no complete message
        if message_content:
            text = "".join(message_content).strip()
            if text:
                logger.info(f"Returning plain text message: {text}")
                return {"message": text}

        logger.warning("No valid content found in response")
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
