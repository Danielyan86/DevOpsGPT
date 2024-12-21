from slack_sdk import WebClient
from config.settings import SLACK_BOT_TOKEN


def send_slack_message(channel_id: str, message: str):
    """Send a simple text message to Slack channel"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        response = client.chat_postMessage(channel=channel_id, text=message)
        return response
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return None


def send_interactive_message(channel_id: str, blocks: list):
    """Send an interactive message with blocks to Slack channel"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        response = client.chat_postMessage(
            channel=channel_id, blocks=blocks, text="Deployment confirmation request"
        )
        return response
    except Exception as e:
        print(f"Error sending interactive message: {str(e)}")
        return None
