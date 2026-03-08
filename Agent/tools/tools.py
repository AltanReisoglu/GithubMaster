import re
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class SecurityScannerInput(BaseModel):
    """Input schema for SecurityScannerTool."""
    code_diff: str = Field(..., description="The git diff string to scan for security issues.")

class SecurityScannerTool(BaseTool):
    name: str = "Security Scanner"
    description: str = "Scans code diffs for potential security vulnerabilities like hardcoded secrets or dangerous functions."
    args_schema: Type[BaseModel] = SecurityScannerInput

    def _run(self, code_diff: str) -> str:
        findings = []
        # Check for hardcoded secrets
        secret_patterns = [
            r'(password|secret|api_key|token|access_key)\s*[:=]\s*["\'][^"\']+["\']',
            r'ghp_[a-zA-Z0-9]{36}', # GitHub PAT
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, code_diff, re.I):
                findings.append("CRITICAL: Potential hardcoded secret or API key detected.")
        
        # Check for dangerous functions
        dangerous_funcs = ["eval(", "exec(", "os.system(", "subprocess.Popen(shell=True"]
        for func in dangerous_funcs:
            if func in code_diff:
                findings.append(f"WARNING: Dangerous function usage detected: {func}")
                
        return "\n".join(findings) if findings else "Security scan passed: No critical issues found."

class ComplexityInput(BaseModel):
    """Input schema for ComplexityTool."""
    code: str = Field(..., description="The full code snippet to analyze for complexity.")

class ComplexityTool(BaseTool):
    name: str = "Complexity Analyzer"
    description: str = "Analyzes the cyclomatic complexity of code snippets. High values mean the code is hard to maintain."
    args_schema: Type[BaseModel] = ComplexityInput

    def _run(self, code: str) -> str:
        # Simple heuristic for complexity: count control flow keywords
        keywords = ['if ', 'for ', 'while ', 'elif ', 'case ', 'except ']
        complexity = 1
        for kw in keywords:
            complexity += code.count(kw)
            
        if complexity > 10:
            return f"Complexity Score: {complexity}. Status: HIGH. Recommendation: Refactor this function into smaller parts."
        elif complexity > 5:
            return f"Complexity Score: {complexity}. Status: MODERATE. Recommendation: Consider simplifying."
        else:
            return f"Complexity Score: {complexity}. Status: LOW. Good readability."