"""
RAG service backed by OpenRAG (https://github.com/langflow-ai/openrag).

OpenRAG is a server-based RAG platform.  Start it before running the agent:
    uv run openrag          # local Python install
    docker compose up       # Docker-based deploy

SDK docs: https://pypi.org/project/openrag-sdk/
"""
import io
import asyncio
import concurrent.futures
import logging

from openrag_sdk import OpenRAGClient
from config import config

logger = logging.getLogger("rag_service")


# -- Async helper -------------------------------------------------------------

def _run_async(coro):
    """
    Run an async coroutine from a synchronous context (e.g. CrewAI tools).
    Works whether or not an event loop is already running.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)


# -- Service ------------------------------------------------------------------

class RAGService:
    """
    Wraps OpenRAG SDK to store commit diffs as searchable documents
    and retrieve past context for agent analysis.
    """

    def _client(self) -> OpenRAGClient:
        return OpenRAGClient(
            api_key=config.OPENRAG_API_KEY,
            base_url=config.OPENRAG_URL,
        )

    def _make_filename(self, repo: str, file_path: str, commit_sha: str) -> str:
        safe_repo = repo.replace("/", "_")
        safe_path = file_path.replace("/", "_").replace(".", "-")
        return f"{safe_repo}__{safe_path}__{commit_sha[:8]}.txt"

    # -- Ingestion -------------------------------------------------------------

    async def _ingest_async(
        self,
        repo: str,
        commit_sha: str,
        file_path: str,
        diff_content: str,
        commit_message: str,
        full_content: str = "",
    ) -> None:
        """Upload one file diff (and full content) to OpenRAG as a plain-text document."""
        document = (
            f"Repository: {repo}\n"
            f"File: {file_path}\n"
            f"Commit SHA: {commit_sha}\n"
            f"Commit Message: {commit_message}\n"
            f"Diff:\n{diff_content[:4000]}\n"
        )
        if full_content:
             document += f"\n--- Full File Content at this commit ---\n{full_content}"
             
        filename = self._make_filename(repo, file_path, commit_sha)
        async with self._client() as client:
            await client.documents.ingest(
                file=io.BytesIO(document.encode("utf-8")),
                filename=filename,
                wait=False,
            )

    def store_commit_diff(
        self,
        repo: str,
        commit_sha: str,
        file_path: str,
        diff_content: str,
        commit_message: str = "",
        full_content: str = "",
    ) -> None:
        """Sync entry-point: persist a commit diff and full state into OpenRAG."""
        try:
            _run_async(self._ingest_async(repo, commit_sha, file_path, diff_content, commit_message, full_content))
        except Exception as e:
            logger.error(f"Failed to ingest diff for {file_path}: {e}")

    # -- Retrieval -------------------------------------------------------------

    async def _search_async(self, file_path: str, code_snippet: str, n_results: int) -> list:
        """Semantic search over past commit documents in OpenRAG."""
        query = f"File: {file_path}\n{code_snippet[:300]}"
        async with self._client() as client:
            results = await client.search.query(query, limit=n_results)
            return [r.text for r in results.results]

    def query_file_history(
        self, file_path: str, code_snippet: str, n_results: int = 3
    ) -> list:
        """Sync entry-point: return past commit docs relevant to the given file/snippet."""
        try:
            return _run_async(self._search_async(file_path, code_snippet, n_results))
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    # -- Async wrappers for FastAPI endpoints ----------------------------------

    async def query_history(self, filename: str, content: str) -> list:
        return await self._search_async(filename, content, n_results=3)

    async def add_to_history(self, filename: str, analysis: str, commit_msg: str) -> None:
        await self._ingest_async(
            repo="internal",
            commit_sha="analysis",
            file_path=filename,
            diff_content=analysis,
            commit_message=commit_msg,
        )


rag_service = RAGService()
