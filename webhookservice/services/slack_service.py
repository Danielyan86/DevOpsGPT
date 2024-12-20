import requests
from config.settings import SLACK_BOT_TOKEN

def send_slack_message(channel_id, message):
    """Send message to Slack channel"""
    try:
        print(f"\n=== Sending Slack Message ===")
        print(f"Channel: {channel_id}")
        print(f"Message content: {message}")

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={
                "channel": channel_id,
                "text": message,
                "mrkdwn": True,
                "response_type": "in_channel",
            },
        )

        print(f"Slack API Response Status: {response.status_code}")
        print(f"Slack API Response Body: {response.text}")

        response_data = response.json()
        if not response_data.get("ok"):
            error = response_data.get("error", "unknown error")
            if error == "not_in_channel":
                print(f"ERROR: Bot needs to be invited to channel {channel_id}")
                join_response = requests.post(
                    "https://slack.com/api/conversations.join",
                    headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                    json={"channel": channel_id},
                )
                print(f"Channel join attempt response: {join_response.text}")
                return send_slack_message(channel_id, message)
            else:
                print(f"ERROR: Slack API error: {error}")

        return response_data.get("ok", False)
    except Exception as e:
        print(f"ERROR in send_slack_message: {str(e)}")
        print(f"Exception type: {type(e)}")
        return False
