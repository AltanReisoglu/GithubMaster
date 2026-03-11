import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header
from config import config

router = APIRouter()

async def verify_signature(request: Request, x_hub_signature_256: str):
    if not config.GITHUB_WEBHOOK_SECRET:
        return True
        
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
    if x_hub_signature_256:
        await verify_signature(request, x_hub_signature_256)
    
    payload = await request.json()
    
    if x_github_event == "push":
        return await handle_push_event(payload)
    elif x_github_event == "pull_request":
        return await handle_pull_request_event(payload)
    
    return {"status": "ignored", "event": x_github_event}

async def handle_push_event(payload: dict):
    from services.github_service import github_service
    from services.rag_service import rag_service
    from utils.file_filter import FileFilter

    commit_sha = payload.get("after")
    repository = payload.get("repository", {}).get("full_name")
    commits = payload.get("commits", [])
    commit_message = commits[-1].get("message", "") if commits else ""

    print(f"Processing push commit {commit_sha} in {repository}")

    if commit_sha and repository:
        diff_text = await github_service.get_commit_diff(repository, commit_sha)
        if diff_text:
            filtered = FileFilter.filter_diff(diff_text)
            for item in filtered:
                rag_service.store_commit_diff(
                    repo=repository,
                    commit_sha=commit_sha,
                    file_path=item["file"],
                    diff_content=item["diff"],
                    commit_message=commit_message,
                )
            print(f"Stored {len(filtered)} file diffs in vector DB for commit {commit_sha}")

    return {"status": "accepted", "event": "push"}

from services.github_service import github_service
from services.ast_service import ast_service
from services.rag_service import rag_service
from agents.crew import review_crew
from utils.file_filter import FileFilter
from services.lifecycle_service import lifecycle_service

async def handle_pull_request_event(payload: dict):
    action = payload.get("action")
    pr_number = payload.get("number")
    repository = payload.get("repository", {}).get("full_name")

    # PR merged — learn from it
    if action == "closed" and payload.get("pull_request", {}).get("merged"):
        commit_msg = payload.get("pull_request", {}).get("title", "")
        print(f"PR #{pr_number} merged. Learning from the changes...")
        await lifecycle_service.learn_from_merged_pr(
            repository, 
            pr_number, 
            commit_msg, 
            "Self-learned from merged PR"
        )
        return {"status": "accepted", "event": "pr_merged"}

    # PR opened or updated — run analysis
    if action in ["opened", "synchronize"]:
        print(f"Processing PR #{pr_number} in {repository}")
        
        diff_text = await github_service.get_pull_request_diff(repository, pr_number)
        if not diff_text:
            return {"status": "error", "message": "Failed to fetch diff"}
            
        filtered_changes = FileFilter.filter_diff(diff_text)
        print(f"Filtered {len(filtered_changes)} files for analysis.")
        
        files_data = []
        for change in filtered_changes:
            path = change['file']
            diff = change['diff']
            
            full_content = await github_service.get_file_content(
                repository, path, payload['pull_request']['head']['sha']
            )
            skeleton = ast_service.get_skeleton(path, full_content) if full_content else ""
            history = await rag_service.query_history(path, diff)
            
            files_data.append({
                "path": path,
                "diff": diff,
                "skeleton": skeleton,
                "history": history
            })
            
        if files_data:
            import asyncio
            loop = asyncio.get_event_loop()
            analysis_result = await loop.run_in_executor(
                None, review_crew.run_review, files_data
            )
            analysis_result = str(analysis_result)
            await github_service.post_pull_request_comment(repository, pr_number, analysis_result)
            
        return {"status": "accepted", "event": "pull_request", "files_processed": len(filtered_changes)}
    
    return {"status": "ignored", "action": action}
