"""
Chapter 16 — Security — Example 2
The Agentic AI Bible (Revised & Expanded Edition 2026)
Companion repository: github.com/agentic-ai-bible/code

Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here

Run:
    python ch16_02_ExecutionResult.py
"""
# Tested with Python 3.11, docker==7.0.0
# Sandboxed code execution tool resistant to privilege escalation
# Requires: Docker installed and accessible to the running process

import docker
import tempfile
import os
import json
import hashlib
import time
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    was_killed: bool  # True if killed due to timeout or resource limit
    sandbox_violations: list[str]  # Any attempted violations we detected


class SandboxedCodeExecutor:
    """Execute untrusted code in a Docker container with strict resource limits.
    
    Security model:
    - Each execution gets a fresh container (no state carryover)
    - Network access is blocked entirely
    - Filesystem is read-only except for a temp work directory
    - CPU and memory are hard-limited
    - No new privileges can be acquired
    - All capabilities dropped
    - Execution time is hard-limited
    
    This is appropriate for executing code submitted by end users or generated
    by an agent as part of a data analysis task. It is NOT appropriate for
    code that requires network access or filesystem writes outside the workspace.
    """
    
    # Docker image to use - must be pre-built with only necessary dependencies
    # Never use 'latest' in production; pin to a specific digest
    SANDBOX_IMAGE = "python:3.11-slim@sha256:abc123"  # Pin to specific digest
    
    def __init__(
        self,
        max_execution_seconds: int = 30,
        max_memory_mb: int = 256,
        max_output_bytes: int = 1024 * 1024,  # 1MB output cap
    ):
        self.client = docker.from_env()
        self.max_execution_seconds = max_execution_seconds
        self.max_memory_mb = max_memory_mb
        self.max_output_bytes = max_output_bytes
    
    def execute(
        self,
        code: str,
        language: str = "python",
        allowed_imports: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """Execute code in a sandboxed container.
        
        allowed_imports: if provided, the code is pre-scanned to ensure
        it only imports from this list. This is defense-in-depth against
        import-based privilege escalation (e.g., importing 'subprocess',
        'os', 'socket').
        """
        violations = []
        
        # Pre-execution static analysis
        if language == "python":
            violations.extend(
                self._check_python_imports(code, allowed_imports or [])
            )
            violations.extend(self._check_dangerous_patterns(code))
        
        if violations and any('CRITICAL' in v for v in violations):
            return ExecutionResult(
                stdout="",
                stderr=f"Execution blocked: {violations[0]}",
                exit_code=-1,
                execution_time_ms=0,
                was_killed=False,
                sandbox_violations=violations,
            )
        
        # Write code to a temporary file that will be mounted read-only
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = Path(tmpdir) / "solution.py"
            code_file.write_text(code)
            
            start_time = time.time()
            container = None
            
            try:
                container = self.client.containers.run(
                    self.SANDBOX_IMAGE,
                    command=["python", "/workspace/solution.py"],
                    volumes={
                        tmpdir: {
                            "bind": "/workspace",
                            "mode": "ro",  # Read-only: code cannot write to its own directory
                        }
                    },
                    # Resource limits
                    mem_limit=f"{self.max_memory_mb}m",
                    memswap_limit=f"{self.max_memory_mb}m",  # Disable swap
                    cpu_period=100000,
                    cpu_quota=50000,  # 50% of one CPU core
                    pids_limit=64,    # Max 64 processes (prevents fork bombs)
                    # Security settings
                    network_disabled=True,           # No network access
                    read_only=True,                  # Read-only root filesystem
                    security_opt=["no-new-privileges:true"],
                    cap_drop=["ALL"],                 # Drop all Linux capabilities
                    user="nobody",                   # Run as unprivileged user
                    # Execution settings
                    detach=True,
                    remove=False,  # We'll remove manually after reading output
                )
                
                # Wait with timeout
                try:
                    exit_result = container.wait(timeout=self.max_execution_seconds)
                    was_killed = False
                    exit_code = exit_result.get("StatusCode", -1)
                except Exception:  # Timeout
                    container.kill()
                    was_killed = True
                    exit_code = -1
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                # Retrieve output (capped at max_output_bytes)
                logs = container.logs(stdout=True, stderr=False)
                errors = container.logs(stdout=False, stderr=True)
                
                stdout = logs.decode('utf-8', errors='replace')[:self.max_output_bytes]
                stderr = errors.decode('utf-8', errors='replace')[:self.max_output_bytes]
                
                return ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time_ms=execution_time_ms,
                    was_killed=was_killed,
                    sandbox_violations=violations,
                )
            
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass  # Best effort cleanup
    
    def _check_python_imports(self, code: str, allowed: list[str]) -> list[str]:
        """Static analysis: check for imports not in the allowed list."""
        import ast
        violations = []
        
        # Dangerous imports that should never be allowed
        ALWAYS_BLOCKED = {
            "subprocess", "os", "sys", "socket", "urllib", "requests",
            "http", "ftplib", "smtplib", "telnetlib", "ctypes",
            "multiprocessing", "threading", "importlib", "pickle",
        }
        
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = (
                        node.names[0].name if isinstance(node, ast.Import)
                        else (node.module or "")
                    ).split(".")[0]  # Get top-level module name
                    
                    if module in ALWAYS_BLOCKED:
                        violations.append(
                            f"CRITICAL: Blocked import '{module}' - privilege escalation risk"
                        )
                    elif allowed and module not in allowed:
                        violations.append(
                            f"WARNING: Import '{module}' not in allowed list"
                        )
        except SyntaxError as e:
            violations.append(f"WARNING: Syntax error in submitted code: {e}")
        
        return violations
    
    def _check_dangerous_patterns(self, code: str) -> list[str]:
        """Check for dangerous code patterns beyond import analysis."""
        import re
        violations = []
        
        DANGEROUS_PATTERNS = [
            (r'__import__\s*\(', "CRITICAL: Dynamic import detected"),
            (r'exec\s*\(', "CRITICAL: exec() call detected"),
            (r'eval\s*\(', "WARNING: eval() call detected"),
            (r'open\s*\(.*["\']w', "WARNING: File write attempted"),
            (r'builtins|__builtins__', "CRITICAL: Builtins access detected"),
        ]
        
        for pattern, message in DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                violations.append(message)
        
        return violations


# Integration with an agent tool registry
def make_code_execution_tool(
    max_seconds: int = 30,
    allowed_imports: list[str] = None
):
    """Factory function that creates a sandboxed code execution tool
    configured for a specific use case.
    
    For data analysis tasks, allowed_imports might be: ['pandas', 'numpy',
    'matplotlib', 'json', 'csv', 'math', 'statistics']
    """
    executor = SandboxedCodeExecutor(max_execution_seconds=max_seconds)
    default_imports = allowed_imports or ['math', 'json', 'csv', 'statistics']
    
    def execute_code(code: str) -> str:
        """Execute Python code in a sandboxed environment.
        
        Only the following imports are allowed: {imports}
        Code must complete within {seconds} seconds.
        Network access is not available.
        """.format(imports=default_imports, seconds=max_seconds)
        
        result = executor.execute(code, allowed_imports=default_imports)
        
        if result.sandbox_violations:
            critical = [v for v in result.sandbox_violations if 'CRITICAL' in v]
            if critical:
                return f"Execution blocked for security reasons: {critical[0]}"
        
        output = []
        if result.was_killed:
            output.append(f"[Execution timed out after {max_seconds}s]")
        if result.stdout:
            output.append(result.stdout)
        if result.stderr and result.exit_code != 0:
            output.append(f"[Error]: {result.stderr[:500]}")
        
        return "\n".join(output) or "(no output)"
    
    return execute_code

if __name__ == '__main__':
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print('Set ANTHROPIC_API_KEY env var to run this example.')
        print('  export ANTHROPIC_API_KEY=your_key_here')
    else:
        result = make_code_execution_tool(3, 3)
        print(result)
