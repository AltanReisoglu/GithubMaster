import asyncio
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from services.github_service import github_service
from services.ast_service import ast_service
from services.rag_service import rag_service
from agents.crew import review_crew
from utils.file_filter import FileFilter

router = APIRouter()

class AgentAnalysisRequest(BaseModel):
    repository: str
    prNumber: Optional[int] = None
    commitId: Optional[str] = None
    filesToAnalyze: List[str]
    eventType: str

def _run_sync_analysis(files_data):
    """Run the blocking CrewAI review in a sync context (will be offloaded to thread)."""
    return str(review_crew.run_review(files_data))

async def process_analysis(request: AgentAnalysisRequest):
    print(f"Starting analysis for {request.repository} on {request.eventType}")
    
    files_data = []
    ref = request.commitId if request.commitId else "main"
    
    # Fetch the real commit diff if we have a commitId
    commit_diff = None
    if request.commitId:
        try:
            commit_diff = await github_service.get_commit_diff(request.repository, request.commitId)
        except Exception as e:
            print(f"Error fetching commit diff: {e}")

    # Parse the diff into per-file diffs
    per_file_diffs = {}
    if commit_diff:
        from utils.file_filter import FileFilter
        parsed = FileFilter.filter_diff(commit_diff)
        for item in parsed:
            per_file_diffs[item['file']] = item['diff']

    for path in request.filesToAnalyze:
        try:
            full_content = await github_service.get_file_content(request.repository, path, ref)
            skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
        except Exception as e:
            print(f"Error fetching file content or parsing AST for {path}: {e}")
            full_content = ""
            skeleton = ""
        
        # Use actual diff if available, otherwise use file content as context
        diff = per_file_diffs.get(path, "")
        if not diff and full_content:
            diff = f"[Full file content for new/modified file: {path}]\n{full_content[:2000]}"
        
        try:
            history = await rag_service.query_history(path, diff)
        except Exception as e:
            print(f"Error querying history: {e}")
            history = []
            
        files_data.append({
            "path": path,
            "diff": diff,
            "skeleton": skeleton,
            "history": history
        })
        
    if files_data:
        try:
            loop = asyncio.get_event_loop()
            analysis_result = await loop.run_in_executor(None, _run_sync_analysis, files_data)
            print("Analysis Result calculated successfully.")
            
            if request.prNumber:
                await github_service.post_pull_request_comment(
                    request.repository, request.prNumber, analysis_result
                )
            else:
                print(f"Analysis completed for commit {request.commitId}:\n{analysis_result}")
        except Exception as e:
            print(f"Error running agent crew: {e}")

@router.post("/review")
async def trigger_agent_review(request: AgentAnalysisRequest, background_tasks: BackgroundTasks):
    print(f"Received analysis request from Java Backend for: {request.repository}")
    background_tasks.add_task(process_analysis, request)
    return {"status": "accepted", "message": "Analysis started in background"}
