from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython
import tree_sitter_c_sharp as tscsharp

try:
    import tree_sitter_java as tsjava
    _JAVA_AVAILABLE = True
except ImportError:
    _JAVA_AVAILABLE = False


class ASTService:
    def __init__(self):
        self.PY_LANGUAGE = Language(tspython.language())
        self.CS_LANGUAGE = Language(tscsharp.language())
        self.JAVA_LANGUAGE = Language(tsjava.language()) if _JAVA_AVAILABLE else None

    def _parse(self, language: Language, code: str):
        parser = Parser(language)
        return parser.parse(bytes(code, "utf8"))

    def _run_query(self, language: Language, tree, query_str: str) -> dict:
        """Execute a query using tree-sitter 0.25+ QueryCursor API.
        Returns a dict of {capture_name: [Node, ...]}"""
        q = Query(language, query_str)
        cursor = QueryCursor(q)
        return cursor.captures(tree.root_node)

    def get_skeleton(self, file_path: str, code: str) -> str:
        if not code:
            return ""
        if file_path.endswith('.py'):
            return self._extract_python_skeleton(code)
        elif file_path.endswith('.cs'):
            return self._extract_csharp_skeleton(code)
        elif file_path.endswith('.java') and self.JAVA_LANGUAGE:
            return self._extract_java_skeleton(code)
        return ""

    def _extract_python_skeleton(self, code: str) -> str:
        tree = self._parse(self.PY_LANGUAGE, code)
        query_str = """
        (class_definition name: (identifier) @class_name)
        (function_definition name: (identifier) @func_name)
        """
        captures = self._run_query(self.PY_LANGUAGE, tree, query_str)
        skeleton = []
        for node in captures.get("class_name", []):
            skeleton.append(f"Class: {node.text.decode('utf8')}")
        for node in captures.get("func_name", []):
            skeleton.append(f"Function: {node.text.decode('utf8')}")
        return "\n".join(skeleton)

    def _extract_csharp_skeleton(self, code: str) -> str:
        tree = self._parse(self.CS_LANGUAGE, code)
        query_str = """
        (class_declaration name: (identifier) @class_name)
        (method_declaration name: (identifier) @method_name)
        """
        captures = self._run_query(self.CS_LANGUAGE, tree, query_str)
        skeleton = []
        for node in captures.get("class_name", []):
            skeleton.append(f"Class: {node.text.decode('utf8')}")
        for node in captures.get("method_name", []):
            skeleton.append(f"Method: {node.text.decode('utf8')}")
        return "\n".join(skeleton)

    def _extract_java_skeleton(self, code: str) -> str:
        tree = self._parse(self.JAVA_LANGUAGE, code)
        query_str = """
        (class_declaration name: (identifier) @class_name)
        (method_declaration name: (identifier) @method_name)
        (interface_declaration name: (identifier) @interface_name)
        """
        captures = self._run_query(self.JAVA_LANGUAGE, tree, query_str)
        skeleton = []
        for node in captures.get("class_name", []):
            skeleton.append(f"Class: {node.text.decode('utf8')}")
        for node in captures.get("interface_name", []):
            skeleton.append(f"Interface: {node.text.decode('utf8')}")
        for node in captures.get("method_name", []):
            skeleton.append(f"Method: {node.text.decode('utf8')}")
        return "\n".join(skeleton)


ast_service = ASTService()
