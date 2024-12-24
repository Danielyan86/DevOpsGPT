import os
import sys
import time
import logging
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.settings import SLACK_BOT_DEPLOY_TOKEN, SLACK_BOT_MONITOR_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Slack client with your bot token
# We'll use deploy token as default for cleanup
api_token = SLACK_BOT_DEPLOY_TOKEN

# Slack API URLs
history_url = "https://slack.com/api/conversations.history"
delete_url = "https://slack.com/api/chat.delete"


def get_channel_messages(channel_id):
    """
    Retrieve all messages from a Slack channel.
    """
    messages = []
    has_more = True
    cursor = None

    while has_more:
        params = {"channel": channel_id, "limit": 200}  # Max limit
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            history_url,
            headers={"Authorization": f"Bearer {api_token}"},
            params=params,
        )
        data = response.json()

        if not data.get("ok"):
            print(f"Error fetching messages: {data.get('error')}")
            break

        messages.extend(data.get("messages", []))
        cursor = data.get("response_metadata", {}).get("next_cursor")
        has_more = bool(cursor)

    return messages


def delete_message(channel_id, ts):
    """
    Delete a specific message by timestamp.
    """
    response = requests.post(
        delete_url,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        json={"channel": channel_id, "ts": ts},
    )
    data = response.json()

    if data.get("ok"):
        print(f"Message deleted successfully: {ts}")
    else:
        print(f"Failed to delete message {ts}: {data.get('error')}")


def delete_all_messages(channel_id):
    """
    Retrieve all messages and delete them from the specified channel.
    """
    print("Fetching messages...")
    messages = get_channel_messages(channel_id)

    if not messages:
        print("No messages found in the channel.")
        return

    print(f"Found {len(messages)} messages. Deleting...")
    for message in messages:
        ts = message.get("ts")
        if ts:
            delete_message(channel_id, ts)
            # Add a short delay to avoid hitting API rate limits
            time.sleep(0.5)


def get_channel_id(channel_name: str) -> str:
    """Get channel ID from channel name"""
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        response = client.conversations_list()
        for channel in response["channels"]:
            if channel["name"] == channel_name.strip("#"):
                return channel["id"]
        return None
    except Exception as e:
        print(f"Error getting channel ID: {str(e)}")
        return None


# Run the script
if __name__ == "__main__":
    channel_name = "chatops"  # Replace with your channel name
    channel_id = get_channel_id(channel_name)

    if channel_id:
        print(f"Found channel ID for #{channel_name}: {channel_id}")
        delete_all_messages(channel_id)
    else:
        print(f"Could not find channel ID for #{channel_name}")
