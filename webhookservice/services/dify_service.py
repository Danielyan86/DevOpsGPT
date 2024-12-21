import json
import requests
from typing import Dict, Optional
from config.settings import DIFY_API_KEY, DIFY_API_ENDPOINT


def parse_deployment_intent(message: str) -> Optional[Dict]:
    """Parse natural language deployment request using local Dify API"""
    try:
        print(f"\n=== Processing Natural Language Request ===")
        print(f"Input message: {message}")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DIFY_API_KEY}",
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
            return None

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
                                print(f"Error parsing thought content: {e}")
                                continue
                except json.JSONDecodeError:
                    continue

        print("No valid parameters found in response")
        return None

    except Exception as e:
        print(f"Error in parse_deployment_intent: {str(e)}")
        print(f"Exception type: {type(e)}")
        return None
