import httpx
from config import config

class GitHubService:
    def __init__(self):
        self.headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.diff" # Default to diff format
        }
        self.api_url = "https://api.github.com"

    async def get_pull_request_diff(self, repository: str, pr_number: int):
        url = f"{self.api_url}/repos/{repository}/pulls/{pr_number}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
            return None

    async def get_commit_diff(self, repository: str, commit_sha: str):
        url = f"{self.api_url}/repos/{repository}/commits/{commit_sha}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.text
            return None

    async def get_file_content(self, repository: str, path: str, ref: str):
        # Get raw content for file
        headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.raw"
        }
        url = f"{self.api_url}/repos/{repository}/contents/{path}?ref={ref}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.text
            return None

    async def post_pull_request_comment(self, repository: str, pr_number: int, body: str):
        url = f"{self.api_url}/repos/{repository}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {config.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            data = {"body": body}
            response = await client.post(url, headers=headers, json=data)
            return response.status_code == 201

github_service = GitHubService()
