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
        print(f"\n=== Processing Natural Language Request ===")
        print(f"Input message: {message}")

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

        print(f"Sending request to Dify with payload: {payload}")

        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,
        )

        print(f"Dify API Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error from Dify API: {response.text}")
            return {"error": response.text}

        thought_content = None

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8").replace("data: ", "")
                try:
                    data = json.loads(line)
                    if data.get("event") == "agent_thought":
                        thought_content = data.get("thought", "")
                        if thought_content:
                            try:
                                thought_json = json.loads(thought_content)
                                parsed_params = {
                                    "branch": thought_json.get("branch", "main"),
                                    "environment": thought_json.get(
                                        "environment", "staging"
                                    ),
                                }
                                print(f"Parsed parameters: {parsed_params}")
                                return parsed_params
                            except json.JSONDecodeError as e:
                                print(f"Non-JSON thought content: {thought_content}")
                                # Return the raw thought content for non-JSON responses
                                return {"message": thought_content}
                except json.JSONDecodeError:
                    continue

        print("No valid parameters found in response")
        return None

    except Exception as e:
        print(f"Error in parse_deployment_intent: {str(e)}")
        print(f"Exception type: {type(e)}")
        return None


def parse_monitoring_intent(message: str) -> Dict[str, Any]:
    """
    Parse monitoring requests using Dify API
    Returns a dictionary containing:
    - metric_name: The name of the metric to query
    - time_range: Time range for the query (in hours)
    - query_type: 'current', 'range', or 'custom'
    Or for non-monitoring queries:
    - type: 'help' or other type
    - message: The response message
    """
    try:
        print(f"\n=== Processing Monitoring Request ===")
        print(f"Input message: {message}")

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

        print(f"Sending request to Dify with payload: {payload}")

        response = requests.post(
            DIFY_API_ENDPOINT,
            headers=headers,
            data=payload,
            stream=True,
        )

        print(f"Dify API Response Status: {response.status_code}")

        if response.status_code != 200:
            print(f"Error from Dify API: {response.text}")
            return {"error": response.text}

        thought_content = None

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8").replace("data: ", "")
                try:
                    data = json.loads(line)
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
                                    print(f"Received help message: {thought_json}")
                                    return thought_json

                                # Parse monitoring parameters
                                if "query_type" in thought_json:
                                    parsed_params = {
                                        "query_type": thought_json.get(
                                            "query_type", "current"
                                        ),
                                        "metric_name": thought_json.get(
                                            "metric_name",
                                            "todo_process_cpu_seconds_total",
                                        ),
                                        "time_range": int(
                                            thought_json.get("time_range", 1)
                                        ),
                                    }
                                    # For custom queries, include the original query
                                    if (
                                        thought_json.get("query_type") == "custom"
                                        and "query" in thought_json
                                    ):
                                        parsed_params["query"] = thought_json["query"]

                                    print(
                                        f"Parsed monitoring parameters: {parsed_params}"
                                    )
                                    return parsed_params

                                # If we got JSON but it's not in the expected format
                                print(f"Unexpected response format: {thought_json}")
                                return {"type": "unknown", "message": str(thought_json)}

                            except json.JSONDecodeError as e:
                                print(f"Non-JSON thought content: {thought_content}")
                                # Return the raw thought content for non-JSON responses
                                return {"type": "text", "message": thought_content}
                except json.JSONDecodeError:
                    continue

        print("No valid parameters found in response")
        return None

    except Exception as e:
        print(f"Error in parse_monitoring_intent: {str(e)}")
        print(f"Exception type: {type(e)}")
        return None
