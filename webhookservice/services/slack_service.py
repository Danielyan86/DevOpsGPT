from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from config.settings import SLACK_BOT_DEPLOY_TOKEN, SLACK_BOT_MONITOR_TOKEN

logger = logging.getLogger(__name__)


def send_slack_message(
    channel_id: str, message: str, blocks: list = None, is_monitor: bool = False
):
    """Send a message to a Slack channel"""
    try:
        token = SLACK_BOT_MONITOR_TOKEN if is_monitor else SLACK_BOT_DEPLOY_TOKEN
        client = WebClient(token=token)
        response = client.chat_postMessage(
            channel=channel_id,
            text=message,
            blocks=blocks,
        )
        return response
    except SlackApiError as e:
        logger.error(f"Error sending message to Slack: {str(e)}")
        raise


def send_interactive_message(
    channel_id: str, blocks: list, fallback_text: str, is_monitor: bool = False
):
    """Send an interactive message to a Slack channel"""
    try:
        token = SLACK_BOT_MONITOR_TOKEN if is_monitor else SLACK_BOT_DEPLOY_TOKEN
        client = WebClient(token=token)
        response = client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=fallback_text,
        )
        return response
    except SlackApiError as e:
        logger.error(f"Error sending interactive message to Slack: {str(e)}")
        raise


def update_message(
    channel_id: str, ts: str, blocks: list, text: str, is_monitor: bool = False
):
    """Update an existing Slack message"""
    try:
        token = SLACK_BOT_MONITOR_TOKEN if is_monitor else SLACK_BOT_DEPLOY_TOKEN
        client = WebClient(token=token)
        response = client.chat_update(
            channel=channel_id,
            ts=ts,
            blocks=blocks,
            text=text,
            replace_original=True,
        )
        return response
    except SlackApiError as e:
        logger.error(f"Error updating Slack message: {str(e)}")
        raise
