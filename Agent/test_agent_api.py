import httpx
import os

# Disable crewai telemetry to avoid hangs
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TELEMETRY_ENABLED"] = "false"

def test_api():
    url = "http://localhost:8001/api/agent/review"
    payload = {
        "repository": "test/repo",
        "prNumber": 123,
        "commitId": "12345abc",
        "filesToAnalyze": ["test.py"],
        "eventType": "pull_request"
    }
    
    try:
        print(f"Sending request to {url}...")
        response = httpx.post(url, json=payload, timeout=30.0)
        print("Response Status:", response.status_code)
        print("Response JSON:", response.json())
    except Exception as e:
        print("Error during request:", e)

if __name__ == "__main__":
    test_api()
