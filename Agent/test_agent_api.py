from fastapi.testclient import TestClient
from main import app

def test_api():
    client = TestClient(app)

    response = client.post(
        "/api/agent/review",
        json={
            "repository": "test/repo",
            "prNumber": None,
            "commitId": "12345abc",
            "filesToAnalyze": ["test.py"],
            "eventType": "push"
        }
    )
    print("Response Status:", response.status_code)
    print("Response JSON:", response.json())

if __name__ == "__main__":
    test_api()
