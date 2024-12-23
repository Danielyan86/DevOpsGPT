from slack_sdk import WebClient
from config.settings import SLACK_BOT_TOKEN
import logging

logger = logging.getLogger(__name__)


def send_slack_message(channel_id: str, message: str, blocks: list = None) -> None:
    """Send a message to a Slack channel"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        params = {
            "channel": channel_id,
            "text": message,
        }
        if blocks:
            params["blocks"] = blocks

        client.chat_postMessage(**params)
    except Exception as e:
        logger.error(f"Error sending Slack message: {str(e)}")
        raise


def send_interactive_message(
    channel_id: str, blocks: list, fallback_text: str = "New message"
):
    """Send an interactive message with blocks to Slack channel"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=fallback_text,  # Adding fallback text for accessibility
        )
        return response
    except Exception as e:
        logger.error(f"Error sending interactive message: {str(e)}")
        return None
