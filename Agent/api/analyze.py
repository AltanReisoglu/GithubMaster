from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from services.github_service import github_service
from services.ast_service import ast_service
from services.rag_service import rag_service
from agents.crew import review_crew

router = APIRouter()

class AgentAnalysisRequest(BaseModel):
    repository: str
    prNumber: Optional[int] = None
    commitId: Optional[str] = None
    filesToAnalyze: List[str]
    eventType: str

async def process_analysis(request: AgentAnalysisRequest):
    print(f"Starting async analysis for {request.repository} on {request.eventType}")
    
    files_data = []
    
    for path in request.filesToAnalyze:
        ref = request.commitId if request.commitId else "main"
        
        try:
            full_content = await github_service.get_file_content(request.repository, path, ref)
            skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
        except Exception as e:
            print(f"Error fetching file content or parsing AST for {path}: {e}")
            full_content = ""
            skeleton = ""
        
        diff = f"Mock file changed: {path}"
        
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
            analysis_result = str(review_crew.run_review(files_data))
            print("Analysis Result calculated successfully.")
            
            if request.prNumber:
                await github_service.post_pull_request_comment(request.repository, request.prNumber, analysis_result)
            else:
                print(f"Analysis completed for commit push {request.commitId}:\n", analysis_result)
        except Exception as e:
            print(f"Error running agent crew: {e}")

@router.post("/review")
async def trigger_agent_review(request: AgentAnalysisRequest, background_tasks: BackgroundTasks):
    print(f"Received analysis request from Java Backend for: {request.repository}")
    background_tasks.add_task(process_analysis, request)
    return {"status": "accepted", "message": "Analysis started in background"}
