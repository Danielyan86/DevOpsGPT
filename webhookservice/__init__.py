from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    from webhookservice.routes.slack_slash_routes import jenkins_bp
    from webhookservice.routes.slack_app_routes import slack_events_bp

    app.register_blueprint(jenkins_bp)
    app.register_blueprint(slack_events_bp)

    return app
