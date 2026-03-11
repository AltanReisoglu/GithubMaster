"""
Integration test — checks tools, AST service, RAG service, crew imports, and API routes.
Run: python test_integration.py
"""
import asyncio
import sys
import traceback

PASS = "[PASS]"
FAIL = "[FAIL]"

def check(label, fn):
    try:
        fn()
        print(f"{PASS} {label}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        traceback.print_exc()
        return False

async def check_async(label, fn):
    try:
        await fn()
        print(f"{PASS} {label}")
        return True
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        traceback.print_exc()
        return False

# ── Tool tests ─────────────────────────────────────────────────────────────────

def test_security_scanner_detects_secret():
    from tools.tools import SecurityScannerTool
    t = SecurityScannerTool()
    result = t._run('api_key = "sk-abc123xyz"')
    assert "CRITICAL" in result, f"Expected CRITICAL, got: {result}"

def test_security_scanner_detects_dangerous_func():
    from tools.tools import SecurityScannerTool
    t = SecurityScannerTool()
    result = t._run("os.system('rm -rf /')")
    assert "WARNING" in result, f"Expected WARNING, got: {result}"

def test_security_scanner_clean():
    from tools.tools import SecurityScannerTool
    t = SecurityScannerTool()
    result = t._run("def add(a, b): return a + b")
    assert "passed" in result.lower(), f"Expected passed, got: {result}"

def test_complexity_high():
    from tools.tools import ComplexityTool
    t = ComplexityTool()
    # Build a deliberately complex function
    code = "def f():\n" + "    if True:\n" * 12
    result = t._run(code)
    assert "HIGH" in result, f"Expected HIGH complexity, got: {result}"

def test_complexity_low():
    from tools.tools import ComplexityTool
    t = ComplexityTool()
    result = t._run("def add(a, b):\n    return a + b\n")
    assert "LOW" in result, f"Expected LOW complexity, got: {result}"

# ── AST service tests ──────────────────────────────────────────────────────────

def test_ast_python():
    from services.ast_service import ast_service
    code = "class Foo:\n    def bar(self): pass\n"
    skeleton = ast_service.get_skeleton("main.py", code)
    assert "Class: Foo" in skeleton and "Function: bar" in skeleton, skeleton

def test_ast_java():
    from services.ast_service import ast_service, _JAVA_AVAILABLE
    if not _JAVA_AVAILABLE:
        print(f"[SKIP] Java AST not available (tree-sitter-java not installed)")
        return
    code = "public class Hello { public void greet() {} }"
    skeleton = ast_service.get_skeleton("Hello.java", code)
    assert "Class: Hello" in skeleton, f"Got: {skeleton}"

def test_ast_unknown_extension():
    from services.ast_service import ast_service
    result = ast_service.get_skeleton("file.rb", "puts 'hello'")
    assert result == "", f"Expected empty for .rb, got: {result}"

def test_ast_empty_code():
    from services.ast_service import ast_service
    result = ast_service.get_skeleton("file.py", "")
    assert result == "", f"Expected empty for empty code, got: {result}"

# ── RAG service tests ──────────────────────────────────────────────────────────

# OpenRAG tests mock the HTTP client so they don't require a running server.
class _FakeSearchResult:
    def __init__(self, text): self.text = text

class _FakeSearchResults:
    def __init__(self, docs): self.results = [_FakeSearchResult(d) for d in docs]

class _FakeDocuments:
    async def ingest(self, **kwargs): pass

class _FakeSearch:
    async def query(self, text, **kwargs):
        return _FakeSearchResults([f"Historical diff for: {text[:50]}"])

class _FakeOpenRAGClient:
    def __init__(self, **kwargs):
        self.documents = _FakeDocuments()
        self.search = _FakeSearch()
    async def __aenter__(self): return self
    async def __aexit__(self, *a): pass

async def test_rag_store_no_error():
    """store_commit_diff should not raise even if OpenRAG is offline (errors are caught)."""
    from unittest.mock import patch
    from services import rag_service as rs_module
    with patch.object(rs_module.rag_service, '_client', return_value=_FakeOpenRAGClient()):
        # Should not raise
        rs_module.rag_service.store_commit_diff(
            repo="testorg/repo",
            commit_sha="abc123",
            file_path="src/auth.py",
            diff_content="-old_hash = md5(pw)\n+new_hash = bcrypt.hash(pw)",
            commit_message="fix: use bcrypt",
        )

async def test_rag_query_returns_list():
    from unittest.mock import patch
    from services import rag_service as rs_module
    with patch.object(rs_module.rag_service, '_client', return_value=_FakeOpenRAGClient()):
        result = rs_module.rag_service.query_file_history("src/auth.py", "bcrypt password")
        assert isinstance(result, list)
        assert len(result) > 0
        assert "Historical diff" in result[0]

async def test_rag_query_history_async():
    from unittest.mock import patch
    from services import rag_service as rs_module
    with patch.object(rs_module.rag_service, '_client', return_value=_FakeOpenRAGClient()):
        result = await rs_module.rag_service.query_history("src/main.py", "XSS")
        assert isinstance(result, list)

async def test_rag_add_to_history_async():
    from unittest.mock import patch
    from services import rag_service as rs_module
    with patch.object(rs_module.rag_service, '_client', return_value=_FakeOpenRAGClient()):
        # Should not raise
        await rs_module.rag_service.add_to_history("src/main.py", "XSS finding", "fix: escape")

def test_code_rag_tool_no_server():
    """CodeRAGTool should return empty gracefully when OpenRAG is offline."""
    from tools.tools import CodeRAGTool
    from unittest.mock import patch
    from services import rag_service as rs_module
    with patch.object(rs_module.rag_service, 'query_file_history', return_value=[]):
        t = CodeRAGTool()
        result = t._run("src/unknown.py", "some snippet")
        assert "No historical commits" in result

def test_code_rag_tool_with_results():
    from tools.tools import CodeRAGTool
    from unittest.mock import patch
    from services import rag_service as rs_module
    mock_docs = [
        "Repository: testorg/repo\nFile: src/db.py\nDiff:\n-raw sql\n+parameterized",
    ]
    with patch.object(rs_module.rag_service, 'query_file_history', return_value=mock_docs):
        t = CodeRAGTool()
        result = t._run("src/db.py", "SQL injection parameterized")
        assert "Historical Entry 1" in result
        assert "parameterized" in result

# ── FileFilter tests ───────────────────────────────────────────────────────────

def test_file_filter_ignores_lock():
    from utils.file_filter import FileFilter
    assert FileFilter.should_ignore("package-lock.json") is True

def test_file_filter_ignores_image():
    from utils.file_filter import FileFilter
    assert FileFilter.should_ignore("src/logo.png") is True

def test_file_filter_ignores_node_modules():
    from utils.file_filter import FileFilter
    assert FileFilter.should_ignore("node_modules/express/index.js") is True

def test_file_filter_keeps_java():
    from utils.file_filter import FileFilter
    assert FileFilter.should_ignore("src/Main.java") is False

def test_file_filter_diff_parse():
    from utils.file_filter import FileFilter
    fake_diff = (
        "diff --git a/src/Main.java b/src/Main.java\n"
        "index 0000000..1234567\n"
        "--- a/src/Main.java\n"
        "+++ b/src/Main.java\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
    )
    result = FileFilter.filter_diff(fake_diff)
    assert len(result) == 1
    assert result[0]["file"] == "src/Main.java"

# ── API route import tests ────────────────────────────────────────────────────

def test_fastapi_app_imports():
    from main import app
    routes = [r.path for r in app.routes]
    assert "/api/agent/review" in routes, f"Missing /api/agent/review. Routes: {routes}"
    assert "/webhooks/github" in routes, f"Missing /webhooks/github. Routes: {routes}"

def test_crew_imports():
    from agents.crew import review_crew, CodeReviewCrew
    assert review_crew is not None
    crew = CodeReviewCrew()
    # Verify agents can be constructed without Ollama running
    sec_agent = crew.security_agent()
    assert sec_agent.role == "OWASP Security Analyst"
    qual_agent = crew.code_quality_agent()
    assert qual_agent.role == "Code Quality & Performance Reviewer"
    lead_agent = crew.lead_reviewer_agent()
    assert lead_agent.role == "Tech Lead Reviewer"

# ── Runner ─────────────────────────────────────────────────────────────────────

async def main():
    results = []

    sync_tests = [
        ("SecurityScanner detects secret",        test_security_scanner_detects_secret),
        ("SecurityScanner detects dangerous func", test_security_scanner_detects_dangerous_func),
        ("SecurityScanner clean code",             test_security_scanner_clean),
        ("ComplexityTool HIGH",                    test_complexity_high),
        ("ComplexityTool LOW",                     test_complexity_low),
        ("CodeRAGTool no server graceful",         test_code_rag_tool_no_server),
        ("CodeRAGTool formats results correctly",  test_code_rag_tool_with_results),
        ("AST Python skeleton",                    test_ast_python),
        ("AST Java skeleton",                      test_ast_java),
        ("AST unknown extension returns empty",    test_ast_unknown_extension),
        ("AST empty code returns empty",           test_ast_empty_code),
        ("FileFilter ignores lock file",           test_file_filter_ignores_lock),
        ("FileFilter ignores image",               test_file_filter_ignores_image),
        ("FileFilter ignores node_modules",        test_file_filter_ignores_node_modules),
        ("FileFilter keeps .java file",            test_file_filter_keeps_java),
        ("FileFilter parses diff correctly",       test_file_filter_diff_parse),
        ("FastAPI routes registered",              test_fastapi_app_imports),
        ("Crew agents construct correctly",        test_crew_imports),
    ]

    for label, fn in sync_tests:
        results.append(check(label, fn))

    async_tests = [
        ("RAG store_commit_diff no error (mocked)",  test_rag_store_no_error),
        ("RAG query_file_history returns list",      test_rag_query_returns_list),
        ("RAG async query_history",                  test_rag_query_history_async),
        ("RAG async add_to_history",                 test_rag_add_to_history_async),
    ]

    for label, fn in async_tests:
        results.append(await check_async(label, fn))

    total = len(results)
    passed = sum(results)
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
