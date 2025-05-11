import logging
from flask import Blueprint

slack_events_bp = Blueprint("slack_events", __name__)
logger = logging.getLogger(__name__)
processed_events = set()

# 导入子路由，确保注册到Blueprint
from .slack_deploy_routes import *
from .slack_monitor_routes import * 