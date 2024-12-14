from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Jenkins Configuration
JENKINS_URL = "http://127.0.0.1:8080/job/Todo_deployment_pipeline/"
JENKINS_USER = "xiaodong"
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")

# Add validation to ensure token exists
if not JENKINS_TOKEN:
    raise ValueError("JENKINS_TOKEN environment variable is not set")


@app.route("/test-jenkins", methods=["GET"])
def test_jenkins():
    # Test Jenkins API
    response = requests.post(
        JENKINS_URL + "build",
        auth=(JENKINS_USER, JENKINS_TOKEN),
        data={"branch": "main", "environment": "staging"},
    )

    return (
        jsonify({"status_code": response.status_code, "response_text": response.text}),
        200,
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)
