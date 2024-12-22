import logging
from functools import wraps
from flask import jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    return decorated_function
