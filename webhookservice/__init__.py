from flask import Flask
from flask_cors import CORS
from webhookservice.routes.monitor_routes import monitor_bp
from webhookservice.routes.slack_slash_routes import slack_slash_bp
from webhookservice.routes.deploy_routes import slack_events_bp
from config.settings import validate_config


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    CORS(app)

    # Validate configuration
    validate_config()

    # Register blueprints
    app.register_blueprint(monitor_bp, url_prefix="/metrics")
    app.register_blueprint(slack_slash_bp, url_prefix="/deploy")
    app.register_blueprint(
        slack_events_bp
    )  # No prefix to handle both /deploy and /monitor paths

    return app
