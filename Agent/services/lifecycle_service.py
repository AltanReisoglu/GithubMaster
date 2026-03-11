import logging
from services.rag_service import rag_service

logger = logging.getLogger("lifecycle")

class LifecycleService:
    @staticmethod
    async def learn_from_merged_pr(repository: str, pr_number: int, commit_msg: str, analysis_summary: str):
        """
        Store the PR analysis and commit details into the Vector DB for future reference.
        """
        logger.info(f"Learning from PR #{pr_number} in {repository}")
        
        # In a real scenario, we might want to iterate over changed files 
        # but for now we store the overall PR analysis as a context for those files.
        await rag_service.add_to_history(
            filename=f"PR_{pr_number}",
            analysis=analysis_summary,
            commit_msg=commit_msg
        )

lifecycle_service = LifecycleService()
