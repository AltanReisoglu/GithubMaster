import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header
from config import config

router = APIRouter()

async def verify_signature(request: Request, x_hub_signature_256: str):
    if not config.GITHUB_WEBHOOK_SECRET:
        return True # Skip verification if no secret is set (not recommended for production)
        
    body = await request.body()
    signature = "sha256=" + hmac.new(
        config.GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(None)
):
    # Verify Webhook Signature
    if x_hub_signature_256:
        await verify_signature(request, x_hub_signature_256)
    
    payload = await request.json()
    
    # Adım 1.2: Payload Analizi
    if x_github_event == "push":
        return await handle_push_event(payload)
    elif x_github_event == "pull_request":
        return await handle_pull_request_event(payload)
    
    return {"status": "ignored", "event": x_github_event}

async def handle_push_event(payload: dict):
    commit_id = payload.get("after")
    repository = payload.get("repository", {}).get("full_name")
    print(f"Processing commit {commit_id} in {repository}")
    # Trigger Phase 1.3 / 1.4 logic here
    return {"status": "accepted", "event": "push"}

from services.github_service import github_service
from services.ast_service import ast_service
from services.rag_service import rag_service
from agents.crew import review_crew
from utils.file_filter import FileFilter

async def handle_pull_request_event(payload: dict):
    action = payload.get("action")
    pr_number = payload.get("number")
    repository = payload.get("repository", {}).get("full_name")
    
    if action in ["opened", "synchronize"]:
        print(f"Processing PR #{pr_number} in {repository}")
        
        # 1.4: Diff Çekimi
        diff_text = await github_service.get_pull_request_diff(repository, pr_number)
        if not diff_text:
            return {"status": "error", "message": "Failed to fetch diff"}
            
        # 1.3: Gürültü Filtreleme
        filtered_changes = FileFilter.filter_diff(diff_text)
        print(f"Filtered {len(filtered_changes)} files for analysis.")
        
        # Phase 2 & 3: Gather Context & Run Review
        files_data = []
        for change in filtered_changes:
            path = change['file']
            diff = change['diff']
            
            # 2.1: AST Extraction
            # We fetch full content to get the skeleton
            full_content = await github_service.get_file_content(repository, path, payload['pull_request']['head']['sha'])
            skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
            
            # 2.3: RAG Query
            history = await rag_service.query_history(path, diff)
            
            files_data.append({
                "path": path,
                "diff": diff,
                "skeleton": skeleton,
                "history": history
            })
            
        # 3.1-3.3: Run Agent Crew
        if files_data:
            analysis_result = str(review_crew.run_review(files_data))
            
            # Phase 4.1: GitHub'a Yorum Yazma
            # We would post a comment here. (Need to implement post_comment in GitHubService)
            await github_service.post_pull_request_comment(repository, pr_number, analysis_result)
            
        return {"status": "accepted", "event": "pull_request", "files_processed": len(filtered_changes)}
    
from services.lifecycle_service import lifecycle_service

async def handle_pull_request_event(payload: dict):
    # ... previous logic ...
    
    if action == "closed" and payload.get("pull_request", {}).get("merged"):
        pr_number = payload.get("number")
        repository = payload.get("repository", {}).get("full_name")
        commit_msg = payload.get("pull_request", {}).get("title", "")
        
        # We might want to retrieve the previous analysis from a DB if we persisted it,
        # but for this demo logic, we'll store what we can.
        print(f"PR #{pr_number} merged. Learning from the changes...")
        await lifecycle_service.learn_from_merged_pr(
            repository, 
            pr_number, 
            commit_msg, 
            "Self-learned from merged PR"
        )
        return {"status": "accepted", "event": "pr_merged"}
        
    return {"status": "ignored", "action": action}
