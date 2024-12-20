import sys
import os

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webhookservice import create_app
from config.settings import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, validate_config

app = create_app()

if __name__ == "__main__":
    validate_config()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
