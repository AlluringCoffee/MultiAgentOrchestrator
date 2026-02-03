import os
import ast
import logging
from typing import Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# Dangerous built-ins and modules that should be blocked
BLOCKED_NAMES = {
    # Dangerous built-ins
    'eval', 'exec', 'compile', '__import__', 'open', 'input',
    'breakpoint', 'memoryview', 'vars', 'locals', 'globals',
    # Module access
    'importlib', 'subprocess', 'os', 'sys', 'shutil',
    'socket', 'urllib', 'requests', 'http', 'ftplib',
    'pickle', 'shelve', 'marshal', 'code', 'codeop',
    'ctypes', 'multiprocessing', 'threading',
}

# Allowed safe built-ins
SAFE_BUILTINS = {
    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
    'callable', 'chr', 'classmethod', 'complex', 'dict', 'dir', 'divmod',
    'enumerate', 'filter', 'float', 'format', 'frozenset', 'getattr',
    'hasattr', 'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'object', 'oct',
    'ord', 'pow', 'property', 'range', 'repr', 'reversed', 'round', 'set',
    'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
    'tuple', 'type', 'zip', 'True', 'False', 'None',
}


class ScriptSecurityError(Exception):
    """Raised when script contains potentially dangerous code."""
    pass


class SafetyVisitor(ast.NodeVisitor):
    """AST visitor that checks for dangerous constructs."""

    def __init__(self):
        self.errors: list = []

    def visit_Import(self, node):
        """Block import statements."""
        for alias in node.names:
            if alias.name.split('.')[0] in BLOCKED_NAMES:
                self.errors.append(f"Import of '{alias.name}' is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Block from...import statements for dangerous modules."""
        if node.module and node.module.split('.')[0] in BLOCKED_NAMES:
            self.errors.append(f"Import from '{node.module}' is not allowed")
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls for dangerous patterns."""
        # Check for direct calls to dangerous functions
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_NAMES:
                self.errors.append(f"Call to '{node.func.id}' is not allowed")
        # Check for attribute access like os.system
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in {'system', 'popen', 'spawn', 'fork', 'exec', 'execl', 'execle', 'execlp', 'execv', 'execve', 'execvp'}:
                self.errors.append(f"Call to '{node.func.attr}' is not allowed")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check for dangerous attribute access."""
        # Block dunder attribute access that could be used for escapes
        if node.attr.startswith('__') and node.attr.endswith('__'):
            if node.attr not in {'__init__', '__str__', '__repr__', '__len__', '__iter__', '__next__', '__getitem__', '__setitem__', '__contains__'}:
                self.errors.append(f"Access to '{node.attr}' is not allowed")
        self.generic_visit(node)


def validate_script(code: str) -> None:
    """
    Validate script code for security issues using AST analysis.
    Raises ScriptSecurityError if dangerous constructs are found.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ScriptSecurityError(f"Syntax error in script: {e}")

    visitor = SafetyVisitor()
    visitor.visit(tree)

    if visitor.errors:
        raise ScriptSecurityError(f"Security violations: {'; '.join(visitor.errors)}")


def create_restricted_builtins() -> Dict[str, Any]:
    """Create a restricted set of built-in functions."""
    import builtins
    restricted = {}
    for name in SAFE_BUILTINS:
        if hasattr(builtins, name):
            restricted[name] = getattr(builtins, name)
    return restricted


class ScriptNode:
    """
    Executes Python logic scripts in a sandboxed environment.

    Security improvements:
    - AST-based code validation before execution
    - Blocked dangerous built-ins and modules
    - Restricted execution environment
    - Controlled file system access
    - Timeout protection (via caller)
    """
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config
        self.enable_security = config.get("enable_security", True)
        self.allowed_paths: Set[str] = set(config.get("allowed_paths", ['.']))

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        engine = context.get('engine')
        node = context.get('node')
        input_text = inputs.get('text') or inputs.get('query', '')
        raw_context = context.get('context_str', '')

        if not engine or not node:
            return {"ok": False, "error": "Missing engine or node in context"}

        await engine.log(node.name, "Executing Python logic script...")

        # Validate script security
        script_code = node.script_code
        if self.enable_security:
            try:
                validate_script(script_code)
            except ScriptSecurityError as e:
                logger.warning(f"Script security violation: {e}")
                return {"ok": False, "error": f"Script blocked: {e}"}

        try:
            # Prepare restricted execution context
            from core.tools.cli import CLITool
            from core.tools.git_tool import GitTool
            from core.tools.hf_tool import HFTool

            allowed_paths = self.allowed_paths

            def shell(command):
                """Executes a shell command and returns output."""
                res = CLITool.execute(command, ".", use_shell=False)
                if res.get("success"):
                    return res.get("stdout", "")
                else:
                    return f"Error (Exit {res.get('returncode')}): {res.get('stderr')}"

            class FileHelper:
                """Restricted file helper with path validation."""

                def _validate_path(self, path: str) -> str:
                    """Validate and normalize path, preventing traversal attacks."""
                    # Resolve to absolute path
                    abs_path = os.path.abspath(path)
                    # Check if path is within allowed directories
                    for allowed in allowed_paths:
                        allowed_abs = os.path.abspath(allowed)
                        if abs_path.startswith(allowed_abs):
                            return abs_path
                    raise PermissionError(f"Access denied: {path} is outside allowed directories")

                def read(self, path: str) -> str:
                    validated = self._validate_path(path)
                    with open(validated, 'r', encoding='utf-8') as f:
                        return f.read()

                def write(self, path: str, content: str) -> None:
                    validated = self._validate_path(path)
                    with open(validated, 'w', encoding='utf-8') as f:
                        f.write(content)

                def list(self, path: str = '.') -> list:
                    validated = self._validate_path(path)
                    return os.listdir(validated)

                def exists(self, path: str) -> bool:
                    try:
                        validated = self._validate_path(path)
                        return os.path.exists(validated)
                    except PermissionError:
                        return False

            # Build restricted globals
            restricted_globals = {"__builtins__": create_restricted_builtins()}

            script_context = {
                "input": input_text,
                "context": raw_context,
                "blackboard": engine.blackboard,
                "output": "",  # Script should populate this
                "node": node,
                "shell": shell,
                "files": FileHelper(),
                "cli": CLITool,
                "git": GitTool,
                "hf": HFTool,
                "print": lambda *args, **kwargs: logger.info(' '.join(str(a) for a in args)),
            }

            # Execute with restricted globals
            exec(script_code, restricted_globals, script_context)

            output = str(script_context.get("output", "Script executed successfully."))
            return {"ok": True, "output": output}
        except ScriptSecurityError as e:
            return {"ok": False, "error": f"Security violation: {e}"}
        except PermissionError as e:
            return {"ok": False, "error": f"Permission denied: {e}"}
        except Exception as e:
            # Don't expose full stack traces in production
            logger.error(f"Script execution error: {e}")
            return {"ok": False, "error": f"Script error: {type(e).__name__}: {str(e)}"}
