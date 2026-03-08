from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from config import config
from tools.tools import SecurityScannerTool, ComplexityTool

class CodeReviewCrew:
    def __init__(self):
        # Configure local LLM via Ollama
        self.llm = Ollama(
            model=config.OLLAMA_MODEL,
            base_url=config.OLLAMA_BASE_URL
        )

    def file_reviewer_agent(self):
        return Agent(
            role='Senior File Reviewer',
            goal='Analyze specific code changes (diffs) for bugs, security vulnerabilities, and performance issues.',
            backstory='You are an expert developer specializing in Python and C#. You excel at spotting subtle logic errors and security flaws in code diffs.',
            allow_delegation=False,
            tools=[SecurityScannerTool(), ComplexityTool()],
            llm=self.llm,
            verbose=True
        )

    def lead_reviewer_agent(self):
        return Agent(
            role='Tech Lead Reviewer',
            goal='Synthesize multiple file review reports into a concise, high-level pull request summary.',
            backstory='You are a seasoned Tech Lead who focuses on architectural consistency, overall code quality, and macro-level impacts of changes.',
            allow_delegation=True,
            llm=self.llm,
            verbose=True
        )

    def review_file_task(self, agent, file_path, diff_content, ast_skeleton, historical_context):
        return Task(
            description=f"""
            Analyze the following changes in file: {file_path}
            
            GIT DIFF:
            {diff_content}
            
            CODE SKELETON (AST):
            {ast_skeleton}
            
            HISTORICAL CONTEXT:
            {historical_context}
            
            Identify any critical bugs, security risks (OWASP), or major performance regressions. 
            Provide your findings in a clear, bulleted report.
            """,
            agent=agent,
            expected_output="A concise report of findings for the specific file."
        )

    def synthesis_task(self, agent, worker_reports):
        return Task(
            description=f"""
            Review the following individual file analysis reports and synthesize them into a single, cohesive Pull Request review.
            Focus on cross-file inconsistencies and overall risk.
            
            WORKER REPORTS:
            {worker_reports}
            
            OUTPUT FORMAT:
            - Summary of changes
            - Critical Issues (if any)
            - Suggestions for improvement
            - Final Verdict (Approve / Request Changes)
            """,
            agent=agent,
            expected_output="A final Markdown review summary for the GitHub PR."
        )

    def run_review(self, files_data):
        """
        Map-Reduce Flow:
        1. Run parallel (sequential in this sync version for now) tasks for each file.
        2. Collect reports.
        3. Lead agent synthesizes.
        """
        reviewer = self.file_reviewer_agent()
        leader = self.lead_reviewer_agent()
        
        worker_tasks = []
        for file in files_data:
            task = self.review_file_task(
                reviewer, 
                file['path'], 
                file['diff'], 
                file['skeleton'], 
                file['history']
            )
            worker_tasks.append(task)
            
        crew = Crew(
            agents=[reviewer, leader],
            tasks=worker_tasks,
            process=Process.sequential, # For now, simple flow
            verbose=True
        )
        
        # This is a bit tricky with CrewAI for true Map-Reduce in one call if we want dynamic tasks.
        # We might need to run the crew for workers first, then run another task for the leader.
        worker_results = crew.kickoff()
        
        # Synthesis Step
        synth_task = self.synthesis_task(leader, worker_results)
        final_crew = Crew(
            agents=[leader],
            tasks=[synth_task],
            verbose=True
        )
        return final_crew.kickoff()

review_crew = CodeReviewCrew()
