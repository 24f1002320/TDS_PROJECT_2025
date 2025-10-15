# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///
 
import requests
import json

def send_task():
    payload = {
        "email": "student@example.com",
        "secret": "irfankhan",
        "task": "captcha-solver-...",
        "round": 1,
        "nonce": "ab12-...",
        "brief": "Create a captcha solver that handles ?url=https://.../image.png. Default to attached sample.",
        "checks": [
            "Repo has MIT license",
            "README.md is professional",
            "Page displays captcha URL passed at ?url=...",
            "Page displays solved captcha text within 15 seconds",
        ],
        "evaluation_url": "https://example.com/notify",
        "attachments": [
            {"name": "sample.png", "url": "data:image/png;base64,iVBw0R..."}
        ]
    }

    try:
        response = requests.post("http://localhost:8000/handle_task", json=payload)
        
        # FIX: Check for successful status code first and use robust printing
        if response.status_code == 200:
            print("Successfully received response (Status 200):")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: Received status code {response.status_code}")
            print("Response text (may not be JSON):")
            print(response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to the server. Is main.py running on port 8000? Details: {e}")
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON response. The server may have crashed or returned non-JSON data.")
        print(f"Raw text received: {response.text[:200]}...") # Limit output for clarity
        print(f"Details: {e}")


if __name__ == "__main__":
    send_task()