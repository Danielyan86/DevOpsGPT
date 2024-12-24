from flask import Blueprint, request, jsonify
import logging
from webhookservice.services.jenkins_service import trigger_jenkins_build

logger = logging.getLogger(__name__)
slack_slash_bp = Blueprint("slack_slash", __name__)


@slack_slash_bp.route("/command", methods=["POST"])
def handle_slash_command():
    """Handle Slack slash commands"""
    try:
        # Extract command parameters
        branch = request.form.get("text", "main")
        channel = request.form.get("channel_name")
        environment = "staging"  # Default to staging for now

        # Trigger Jenkins build
        response = trigger_jenkins_build(
            branch=branch, environment=environment, channel=f"#{channel}"
        )

        if response.success:
            return jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"🚀 Deployment started for branch `{branch}` to `{environment}`\nBuild number: {response.build_number}",
                }
            )
        else:
            return jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"❌ Deployment failed: {response.message}",
                }
            )

    except Exception as e:
        logger.error(f"Error handling slash command: {str(e)}", exc_info=True)
        return (
            jsonify(
                {
                    "response_type": "in_channel",
                    "text": f"❌ Error processing command: {str(e)}",
                }
            ),
            500,
        )
