# app.py
from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse

app = Flask(__name__)


def validate_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def test_api(url):
    try:
        if not validate_url(url):
            return {"error": "Invalid URL format. Please include http:// or https://"}

        response = requests.get(url, timeout=10)
        result = {
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "content": (
                response.json()
                if response.headers.get("Content-Type", "").startswith(
                    "application/json"
                )
                else response.text
            ),
        }
        return result
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to the server"}
    except Exception as e:
        return {"error": str(e)}


@app.route("/run_test", methods=["POST"])
def run_test():
    # Try to get URL from either JSON or form data
    if request.is_json:
        data = request.get_json()
        url = data.get("url")
    else:
        url = request.form.get("url") or request.values.get("url")

    if not url:
        return jsonify({"error": "URL is required in request body"}), 400

    result = test_api(url)
    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
