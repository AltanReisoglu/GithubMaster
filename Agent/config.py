import os
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:7b")
    # OpenRAG server (run with: uv run openrag  OR  docker compose up)
    OPENRAG_URL = os.getenv("OPENRAG_URL", "http://localhost:3000")
    OPENRAG_API_KEY = os.getenv("OPENRAG_API_KEY", "")

config = Config()
