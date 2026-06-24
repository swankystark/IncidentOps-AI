import ast
import re
from typing import Optional, Tuple, Dict
from pydantic import BaseModel
from .gemini import llm_service

class FunctionIdentification(BaseModel):
    function_name: str
    explanation: str

class LineRangeIdentification(BaseModel):
    start_line: int
    end_line: int
    explanation: str

class CodeTargetingService:
    @staticmethod
    def identify_function_regex(logs: str, affected_file: str) -> Optional[str]:
        if not logs:
            return None
        file_basename = affected_file.split("/")[-1]
        pattern = rf'File ".*{re.escape(file_basename)}", line \d+, in (\w+)'
        matches = re.findall(pattern, logs)
        if matches:
            # Last match is usually the deepest frame in the application code
            return matches[-1]
        return None

    @staticmethod
    def identify_function_llm(source_code: str, root_cause: str, logs: str) -> Optional[str]:
        prompt = f"""
        Given the following source code, root cause, and error logs, identify the exact name of the Python function or class that needs to be modified.
        Return ONLY the function name in the JSON structure. If you cannot determine it, return an empty string.

        --- Root Cause ---
        {root_cause}

        --- Logs ---
        {logs}
        
        --- Source Code ---
        ```python
        {source_code}
        ```
        """
        try:
            output = llm_service.generate_structured(prompt, FunctionIdentification)
            return output.function_name if output.function_name else None
        except Exception:
            return None

    @staticmethod
    def get_function_bounds(source_code: str, function_name: str) -> Optional[Tuple[int, int]]:
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return None

        class FuncVisitor(ast.NodeVisitor):
            def __init__(self):
                self.bounds = None

            def visit_FunctionDef(self, node):
                if node.name == function_name:
                    self.bounds = (node.lineno, getattr(node, "end_lineno", node.lineno))
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                if node.name == function_name:
                    self.bounds = (node.lineno, getattr(node, "end_lineno", node.lineno))
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                if node.name == function_name:
                    self.bounds = (node.lineno, getattr(node, "end_lineno", node.lineno))
                self.generic_visit(node)

        visitor = FuncVisitor()
        visitor.visit(tree)
        return visitor.bounds

    @classmethod
    def identify_line_range_llm(cls, source_code: str, root_cause: str) -> Optional[Tuple[int, int]]:
        prompt = f"""
        Given the following source code and root cause, identify the exact starting and ending line numbers (1-indexed) of the block that needs to be replaced.
        
        --- Root Cause ---
        {root_cause}
        
        --- Source Code (with line numbers) ---
        """
        lines = source_code.splitlines()
        for i, line in enumerate(lines):
            prompt += f"{i+1}: {line}\n"
            
        try:
            output = llm_service.generate_structured(prompt, LineRangeIdentification)
            if 1 <= output.start_line <= output.end_line <= len(lines):
                return (output.start_line, output.end_line)
            return None
        except Exception:
            return None

    @classmethod
    def target_code(cls, source_code: str, affected_file: str, root_cause: str, logs: str) -> Dict:
        """
        Returns a dict containing:
        - function_name (if applicable)
        - start_line (1-indexed)
        - end_line (1-indexed)
        - target_content (the exact string block)
        """
        lines = source_code.splitlines(keepends=True)
        
        if affected_file.endswith(".py"):
            # 1. Deterministic regex
            func_name = cls.identify_function_regex(logs, affected_file)
            
            # 2. LLM fallback
            if not func_name:
                func_name = cls.identify_function_llm(source_code, root_cause, logs)

            if func_name:
                bounds = cls.get_function_bounds(source_code, func_name)
                if bounds:
                    start_line, end_line = bounds
                    target_content = "".join(lines[start_line - 1 : end_line])
                    return {
                        "function_name": func_name,
                        "start_line": start_line,
                        "end_line": end_line,
                        "target_content": target_content
                    }
                    
        # 3. Fallback for non-python or when function targeting fails
        # Use LLM to extract exact line ranges based on root cause
        bounds = cls.identify_line_range_llm(source_code, root_cause)
        if bounds:
            start_line, end_line = bounds
            target_content = "".join(lines[start_line - 1 : end_line])
            return {
                "function_name": None,
                "start_line": start_line,
                "end_line": end_line,
                "target_content": target_content
            }
            
        # Absolute fallback: Target the entire file
        return {
            "function_name": None,
            "start_line": 1,
            "end_line": len(lines),
            "target_content": source_code
        }
