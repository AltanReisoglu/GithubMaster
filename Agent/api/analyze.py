import asyncio
import logging
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from services.github_service import github_service
from services.ast_service import ast_service
from services.rag_service import rag_service
from agents.crew import review_crew
from utils.file_filter import FileFilter

router = APIRouter()
logger = logging.getLogger("analyze")

class AgentAnalysisRequest(BaseModel):
    repository: str
    prNumber: Optional[int] = None
    commitId: Optional[str] = None
    filesToAnalyze: List[str] = []
    eventType: str

def _run_sync_analysis(files_data):
    """Run the blocking CrewAI review in a sync context (will be offloaded to thread)."""
    return str(review_crew.run_review(files_data))

async def process_analysis(request: AgentAnalysisRequest):
    logger.info(f"Starting analysis for {request.repository} on {request.eventType}")

    files_data = []

    # ─── PR event: Java gönderdiği dosya listesi boşsa, diff'i kendimiz çekeriz ───
    if request.eventType == "pull_request" and request.prNumber and not request.filesToAnalyze:
        logger.info(f"PR #{request.prNumber} diff çekiliyor...")

        diff_text = await github_service.get_pull_request_diff(request.repository, request.prNumber)
        if not diff_text:
            logger.error(f"PR #{request.prNumber} için diff alınamadı.")
            return

        filtered_changes = FileFilter.filter_diff(diff_text)
        logger.info(f"PR #{request.prNumber} — {len(filtered_changes)} dosya analiz edilecek.")

        ref = request.commitId or "main"
        for change in filtered_changes:
            path = change['file']
            full_content = await github_service.get_file_content(request.repository, path, ref)
            skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
            files_data.append({
                "path": path,
                "diff": change['diff'],
                "skeleton": skeleton,
            })

    # ─── Push event veya Java'nın dosya listesi gönderdiği durumlar ───
    else:
        ref = request.commitId if request.commitId else "main"

        # Fetch the real commit diff if we have a commitId
        commit_diff = None
        if request.commitId:
            try:
                commit_diff = await github_service.get_commit_diff(request.repository, request.commitId)
            except Exception as e:
                logger.error(f"Error fetching commit diff for {request.commitId}: {e}")

        # Parse the diff into per-file diffs
        per_file_diffs = {}
        if commit_diff:
            parsed = FileFilter.filter_diff(commit_diff)
            for item in parsed:
                per_file_diffs[item['file']] = item['diff']

        for path in request.filesToAnalyze:
            try:
                full_content = await github_service.get_file_content(request.repository, path, ref)
                skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
            except Exception as e:
                logger.error(f"Error fetching file content or parsing AST for {path}: {e}")
                full_content = ""
                skeleton = ""

            # Use actual diff if available, otherwise use file content as context
            diff = per_file_diffs.get(path, "")
            if not diff and full_content:
                diff = f"[Full file content for new/modified file: {path}]\n{full_content[:2000]}"

            files_data.append({
                "path": path,
                "diff": diff,
                "skeleton": skeleton
            })

    if files_data:
        try:
            loop = asyncio.get_event_loop()
            analysis_result = await loop.run_in_executor(None, _run_sync_analysis, files_data)
            logger.info("Analysis Result calculated successfully.")

            if request.prNumber:
                await github_service.post_pull_request_comment(
                    request.repository, request.prNumber, analysis_result
                )
                logger.info(f"PR #{request.prNumber} yorumu başarıyla gönderildi.")
            else:
                logger.info(f"Analysis completed for commit {request.commitId}")
        except Exception as e:
            logger.error(f"Error running agent crew: {e}")
    else:
        logger.warning("Analiz edilecek dosya bulunamadı.")

@router.post("/review")
async def trigger_agent_review(request: AgentAnalysisRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received analysis request from Java Backend for: {request.repository} (event={request.eventType})")
    background_tasks.add_task(process_analysis, request)
    return {"status": "accepted", "message": "Analysis started in background"}

