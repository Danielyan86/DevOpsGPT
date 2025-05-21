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
        final_message = None

        logger.info("Starting to process Dify API response stream")
        
        def handle_thought_content(thought_content: str) -> Optional[Dict]:
            if not thought_content:
                return None
                
            try:
                thought_json = json.loads(thought_content)
                if not thought_json:
                    return None
                    
                if "type" in thought_json:
                    logger.info(f"Returning thought response: {thought_json}")
                    return thought_json
                    
                if "branch" in thought_json or "environment" in thought_json:
                    deployment_params = {
                        "branch": thought_json.get("branch", "main"),
                        "environment": thought_json.get("environment", "staging"),
                        "channel": thought_json.get("channel", "#chatops"),
                    }
                    logger.info(f"Returning deployment parameters: {deployment_params}")
                    return deployment_params
                    
            except json.JSONDecodeError:
                if thought_content not in message_content:
                    logger.debug(f"Adding thought content to message_content: {thought_content}")
                    message_content.append(thought_content)
                    
            return None
            
        def clean_text(text: str) -> str:
            if not text:
                return ""
                
            # Find the well-formatted version of the text
            formatted_text = None
            for possible_text in text.split("I can help you"):
                if "deploy applications" in possible_text and "Try commands like:" in possible_text:
                    formatted_text = "I can help you" + possible_text
                    break

            if not formatted_text:
                # If we couldn't find a well-formatted version, clean up the text as best we can
                lines = text.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if not line or line in cleaned_lines:
                        continue
                    if line.startswith("-"):
                        if not line.startswith("- "):
                            line = "- " + line[1:].strip()
                    cleaned_lines.append(line)
                return "\n".join(cleaned_lines)

            # Clean up the formatted text
            lines = []
            current_line = ""
            for char in formatted_text:
                if char == "-" and current_line.strip():
                    if current_line.strip():
                        lines.append(current_line.strip())
                    current_line = "-"
                else:
                    current_line += char
            if current_line.strip():
                lines.append(current_line.strip())

            # Clean up each line
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line or line in cleaned_lines:
                    continue
                if line.startswith("-"):
                    if not line.startswith("- "):
                        line = "- " + line[1:].strip()
                cleaned_lines.append(line)

            return "\n".join(cleaned_lines)

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")
            logger.debug(f"Raw response line: {line}")

            # Handle ping events
            if line.startswith("event: ping"):
                continue

            # Remove "data: " prefix if present
            if line.startswith("data: "):
                line = line.replace("data: ", "")

            try:
                data = json.loads(line)
                event_type = data.get("event")
                logger.debug(f"Processing event type: {event_type}")

                if event_type == "agent_thought":
                    result = handle_thought_content(data.get("thought", ""))
                    if result:
                        return result
                        
                elif event_type == "agent_message":
                    answer = data.get("answer", "").strip()
                    logger.debug(f"Received agent message: {answer}")
                    if answer and answer not in message_content:
                        logger.debug(f"Adding agent message to message_content: {answer}")
                        message_content.append(answer)
                        
                elif event_type == "end":
                    final_message = data.get("answer", "").strip()
                    logger.debug(f"Received end message: {final_message}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from line: {line}, error: {str(e)}")
                continue

        # If we get here and have message content
        if message_content or final_message:
            # Use final message if available, otherwise join message content
            text = final_message if final_message else "".join(message_content).strip()
            logger.debug(f"Combined raw text before cleaning: {text}")

            if text:
                try:
                    # Try to parse as JSON first
                    json_content = json.loads(text)
                    logger.info(f"Returning JSON message: {json_content}")
                    return json_content
                except json.JSONDecodeError:
                    cleaned_text = clean_text(text)
                    logger.debug(f"Final cleaned text: {cleaned_text}")
                    logger.info(f"Returning plain text message: {cleaned_text}")
                    return {"message": cleaned_text}

        logger.warning("No valid content found in response")
        return None

    except requests.Timeout:
        logger.error("Request to Dify API timed out after 30 seconds")
        return {"error": "Request timed out"}
    except Exception as e:
        logger.error(f"Error in parse_deployment_intent: {str(e)}", exc_info=True)
        return None


def extract_json_from_markdown(text: str) -> Optional[Dict]:
    """Extract JSON from markdown code blocks or plain text"""
    try:
        # Try to parse as direct JSON first
        return json.loads(text)
    except json.JSONDecodeError:
        # Look for JSON in markdown code blocks
        if "```json" in text:
            # Extract content between ```json and ```
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                json_str = text[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        # Try to find JSON-like content without markdown
        try:
            # Look for content between curly braces
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = text[start:end].strip()
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
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

        message_content = []
        
        def handle_thought_content(thought_content: str) -> Optional[Dict]:
            if not thought_content:
                return None
                
            thought_json = extract_json_from_markdown(thought_content)
            if not thought_json:
                return None
                
            if "type" in thought_json and thought_json["type"] == "help":
                return thought_json
                
            if "query_type" in thought_json:
                return {
                    "type": "monitoring",
                    "query_type": thought_json.get("query_type", "current"),
                    "metric": thought_json.get("metric", "all"),
                    "hours": int(thought_json.get("hours", 1)),
                    "original_message": message
                }
                
            return {"type": "unknown", "message": str(thought_json)}
            
        def handle_final_message(final_message: str) -> Optional[Dict]:
            if not final_message:
                return None
                
            final_json = extract_json_from_markdown(final_message)
            if not final_json:
                return None
                
            if "type" not in final_json:
                return None
                
            if final_json["type"] == "help":
                return final_json
                
            if final_json["type"] == "monitoring":
                return {
                    "type": "monitoring",
                    "query_type": final_json.get("query_type", "current"),
                    "metric": final_json.get("metric", "all"),
                    "hours": int(final_json.get("hours", 1)),
                    "original_message": message
                }
                
            return None

        for line in response.iter_lines():
            if not line:
                continue
                
            line_str = line.decode("utf-8").replace("data: ", "")
            try:
                data = json.loads(line_str)
                event_type = data.get("event")
                
                if event_type == "agent_thought":
                    result = handle_thought_content(data.get("thought", ""))
                    if result:
                        return result
                        
                elif event_type == "message":
                    message_content.append(data.get("answer", ""))
                    
                elif event_type == "end":
                    result = handle_final_message(data.get("answer", ""))
                    if result:
                        return result
                    message_content.append(data.get("answer", ""))
                    
            except json.JSONDecodeError:
                continue

        # If we have message content but no JSON was found
        if message_content:
            return {"type": "text", "message": "".join(message_content)}

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
        def format_range_metrics(metrics_data: dict) -> tuple[str, str]:
            series = metrics_data["data"]["result"][0]
            metric_name = series["metric"].get("__name__", "unknown")
            values = series["values"]

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
            return metrics_json, query

        def format_instant_metrics(metrics_data: dict) -> tuple[str, str]:
            metrics_json = json.dumps(metrics_data)
            query = f"Please analyze these monitoring metrics and provide insights: {metrics_json}"
            return metrics_json, query

        def process_dify_response(response) -> list:
            analysis = []
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line_str = line.decode("utf-8").replace("data: ", "")
                try:
                    data = json.loads(line_str)
                    event_type = data.get("event")
                    
                    if event_type == "message":
                        current = data.get("answer", "")
                        if current:
                            analysis.append(current)
                    elif event_type == "agent_thought":
                        thought = data.get("thought", "")
                        if thought:
                            analysis.append(thought)
                    elif event_type == "end":
                        final_answer = data.get("answer", "")
                        if final_answer:
                            analysis.append(final_answer)
                except json.JSONDecodeError:
                    continue
            return analysis

        # Format metrics based on type
        if metrics.get("data", {}).get("resultType") == "matrix" and metrics.get("data", {}).get("result"):
            metrics_json, query = format_range_metrics(metrics)
        else:
            metrics_json, query = format_instant_metrics(metrics)

        # Prepare and send request to Dify API
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
        analysis = process_dify_response(response)
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
