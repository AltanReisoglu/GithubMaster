from tree_sitter import Language, Parser
import tree_sitter_python as tspython
import tree_sitter_c_sharp as tscsharp

class ASTService:
    def __init__(self):
        # Initialize languages
        self.PY_LANGUAGE = Language(tspython.language())
        self.CS_LANGUAGE = Language(tscsharp.language())
        
        self.parser = Parser()

    def get_skeleton(self, file_path: str, code: str) -> str:
        if file_path.endswith('.py'):
            return self._extract_python_skeleton(code)
        elif file_path.endswith('.cs'):
            return self._extract_csharp_skeleton(code)
        return ""

    def _extract_python_skeleton(self, code: str) -> str:
        self.parser.set_language(self.PY_LANGUAGE)
        tree = self.parser.parse(bytes(code, "utf8"))
        
        # Queries to find classes and functions
        query_str = """
        (class_definition
          name: (identifier) @class_name)
        (function_definition
          name: (identifier) @func_name)
        """
        query = self.PY_LANGUAGE.query(query_str)
        captures = query.captures(tree.root_node)
        
        skeleton = []
        for node, tag in captures:
            if tag == "class_name":
                skeleton.append(f"Class: {node.text.decode('utf8')}")
            elif tag == "func_name":
                skeleton.append(f"Function: {node.text.decode('utf8')}")
                
        return "\n".join(skeleton)

    def _extract_csharp_skeleton(self, code: str) -> str:
        self.parser.set_language(self.CS_LANGUAGE)
        tree = self.parser.parse(bytes(code, "utf8"))
        
        # Simplified query for C# classes and methods
        query_str = """
        (class_declaration
          name: (identifier) @class_name)
        (method_declaration
          name: (identifier) @method_name)
        """
        query = self.CS_LANGUAGE.query(query_str)
        captures = query.captures(tree.root_node)
        
        skeleton = []
        for node, tag in captures:
            if tag == "class_name":
                skeleton.append(f"Class: {node.text.decode('utf8')}")
            elif tag == "method_name":
                skeleton.append(f"Method: {node.text.decode('utf8')}")
                
        return "\n".join(skeleton)

ast_service = ASTService()
