# test_api.py
import requests
import sys


def test_api(url):
    try:
        response = requests.get(url)
        result = {
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "content": (
                response.json()
                if response.headers.get("Content-Type") == "application/json"
                else response.text
            ),
        }
        return result
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_api.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    result = test_api(url)
    print(result)
