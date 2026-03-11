from crewai import Agent, Task, Crew, Process, LLM
from config import config
from tools.tools import SecurityScannerTool, ComplexityTool, CodeRAGTool


class CodeReviewCrew:
    def __init__(self):
        # CrewAI 1.x uses its own LLM abstraction.
        # Model format: "ollama/<model_name>"
        self.llm = LLM(
            model=f"ollama/{config.OLLAMA_MODEL}",
            base_url=config.OLLAMA_BASE_URL,
            temperature=0.1,
        )

    def security_agent(self):
        return Agent(
            role='OWASP Security Analyst',
            goal=(
                'Detect security vulnerabilities in code changes based on '
                'OWASP Top 10: injection flaws (SQL, XSS, command injection), '
                'broken access control, cryptographic failures, insecure deserialization, '
                'hardcoded secrets, SSRF, and insecure dependencies.'
            ),
            backstory=(
                'You are a senior application security engineer with deep expertise in '
                'OWASP standards and secure coding practices across Python, Java, C, and C++. '
                'You review code diffs systematically, flagging real vulnerabilities with '
                'CWE identifiers and concrete remediation steps. You avoid false positives. '
                'You use the Code History RAG tool to check if the same file had past vulnerabilities.'
            ),
            allow_delegation=False,
            tools=[SecurityScannerTool(), CodeRAGTool()],
            llm=self.llm,
            verbose=True
        )

    def code_quality_agent(self):
        return Agent(
            role='Code Quality & Performance Reviewer',
            goal=(
                'Analyze code changes for bugs, logic errors, performance regressions, '
                'code smells, and maintainability issues. Focus on correctness first, '
                'then readability and performance.'
            ),
            backstory=(
                'You are a senior software engineer who has reviewed thousands of pull requests. '
                'You excel at spotting subtle bugs like off-by-one errors, null pointer issues, '
                'race conditions, resource leaks, and anti-patterns. You use the code skeleton '
                'and historical context to understand architectural impact. '
                'You query Code History RAG to see if this bug pattern appeared in this file before.'
            ),
            allow_delegation=False,
            tools=[ComplexityTool(), CodeRAGTool()],
            llm=self.llm,
            verbose=True
        )

    def lead_reviewer_agent(self):
        return Agent(
            role='Tech Lead Reviewer',
            goal=(
                'Synthesize security and quality reports into a clear, actionable '
                'pull request review with a final verdict.'
            ),
            backstory=(
                'You are a Tech Lead responsible for final code review decisions. '
                'You weigh security severity, code quality impact, and business risk '
                'to produce a balanced review. You output well-structured Markdown.'
            ),
            allow_delegation=False,
            llm=self.llm,
            verbose=True
        )

    def _create_security_task(self, agent, file_path, diff_content, skeleton):
        return Task(
            description=f"""Perform a security audit on the following code changes.

FILE: {file_path}

GIT DIFF:
```
{diff_content}
```

CODE STRUCTURE (AST):
{skeleton}

Your analysis MUST cover:
1. Injection vulnerabilities (SQL, XSS, command injection, code injection)
2. Hardcoded secrets, API keys, or tokens
3. Insecure cryptographic usage
4. Broken access control patterns
5. Insecure deserialization
6. Path traversal or SSRF risks

For each finding:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- CWE ID (if applicable)
- Affected line/code snippet
- Remediation recommendation

If no issues are found, state "No security issues detected."
""",
            agent=agent,
            expected_output="A structured security audit report for the file.",
            async_execution=True
        )

    def _create_quality_task(self, agent, file_path, diff_content, skeleton):
        return Task(
            description=f"""Review the following code changes for quality issues.

FILE: {file_path}

GIT DIFF:
```
{diff_content}
```

CODE STRUCTURE (AST):
{skeleton}

Feel free to use the `Code History RAG` tool if you need to understand previous variations of this file.

Your analysis MUST cover:
1. Logic errors and potential bugs
2. Null/None safety issues  
3. Resource leaks (unclosed connections, file handles)
4. Performance regressions (N+1 queries, unnecessary allocations)
5. Error handling gaps
6. Code complexity and readability

For each finding, provide:
- Severity: BUG / WARNING / INFO
- Description
- Suggested fix

If the code is clean, state "No quality issues detected."
""",
            agent=agent,
            expected_output="A structured code quality report for the file.",
            async_execution=True
        )

    def _create_synthesis_task(self, agent, all_reports):
        return Task(
            description=f"""You are given the combined security and quality analysis reports
for all changed files. Produce a final pull request review.

INDIVIDUAL REPORTS:
{all_reports}

OUTPUT FORMAT (Markdown):
## Code Review Summary

### Security Findings
(List critical/high findings first, then medium/low)

### Code Quality Findings  
(List bugs first, then warnings, then info)

### Files Reviewed
(Bullet list of files with their status)

### Verdict
**APPROVE** / **REQUEST CHANGES** / **NEEDS DISCUSSION**
(Explain your reasoning in 1-2 sentences)
""",
            agent=agent,
            expected_output="A final Markdown review summary for the GitHub PR."
        )

    def run_review(self, files_data: list) -> str:
        """
        Map-Reduce review:
        1. MAP: For each file, run security + quality analysis in parallel agents
        2. REDUCE: Lead synthesizes all reports into a single PR review
        """
        security_agent = self.security_agent()
        quality_agent = self.code_quality_agent()
        leader = self.lead_reviewer_agent()

        # MAP phase — collect per-file tasks
        all_tasks = []
        agents_in_crew = [security_agent, quality_agent]

        for file in files_data:
            sec_task = self._create_security_task(
                security_agent,
                file['path'],
                file['diff'],
                file['skeleton']
            )
            qual_task = self._create_quality_task(
                quality_agent,
                file['path'],
                file['diff'],
                file['skeleton']
            )
            all_tasks.extend([sec_task, qual_task])

        # Run all file-level tasks
        map_crew = Crew(
            agents=agents_in_crew,
            tasks=all_tasks,
            process=Process.sequential,
            verbose=True
        )
        map_results = map_crew.kickoff()

        # REDUCE phase — synthesize
        synth_task = self._create_synthesis_task(leader, str(map_results))
        reduce_crew = Crew(
            agents=[leader],
            tasks=[synth_task],
            verbose=True
        )
        return str(reduce_crew.kickoff())


review_crew = CodeReviewCrew()
