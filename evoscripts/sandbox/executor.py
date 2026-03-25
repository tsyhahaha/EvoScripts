"""Safe code execution sandbox using subprocess."""

import json
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

from evoscripts.config import settings
from evoscripts.orchestrator.state import CleanerResult, Sample


@dataclass
class ExecutionResult:
    """Result of executing a script."""

    success: bool
    stdout: str
    stderr: str
    return_code: int
    timed_out: bool = False


class SandboxExecutor:
    """Execute Python scripts in a sandboxed subprocess."""

    def __init__(self, timeout: int | None = None):
        """Initialize the sandbox executor.

        Args:
            timeout: Execution timeout in seconds.
        """
        self.timeout = timeout or settings.sandbox_timeout

    def validate_syntax(self, code: str) -> tuple[bool, str]:
        """Check if the code has valid Python syntax.

        Args:
            code: Python source code.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            compile(code, "<string>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    def execute_script(self, code: str) -> ExecutionResult:
        """Execute a Python script in a subprocess.

        Args:
            code: Python source code to execute.

        Returns:
            ExecutionResult with stdout, stderr, and status.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            result = subprocess.run(
                ["python", script_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {self.timeout} seconds",
                return_code=-1,
                timed_out=True,
            )
        finally:
            Path(script_path).unlink(missing_ok=True)

    def run_cleaner_on_samples(
        self,
        cleaner_code: str,
        samples: list[Sample],
    ) -> list[CleanerResult]:
        """Run the cleaner script on a batch of samples.

        The cleaner script should define a function:
            def is_target(data: dict) -> bool

        Args:
            cleaner_code: The cleaner script source code.
            samples: List of samples to process.

        Returns:
            List of CleanerResults.
        """
        # Create wrapper code that imports the cleaner and processes samples
        samples_json = json.dumps([s.data for s in samples], ensure_ascii=False)

        wrapper_code = textwrap.dedent(f'''
            import json
            import sys

            # Cleaner code
            {cleaner_code}

            # Samples to process
            samples = json.loads({repr(samples_json)})

            # Run cleaner on each sample
            results = []
            for i, sample in enumerate(samples):
                try:
                    is_tgt = is_target(sample)
                    results.append({{"index": i, "is_target": is_tgt, "error": None}})
                except Exception as e:
                    results.append({{"index": i, "is_target": False, "error": str(e)}})

            # Output results as JSON
            print(json.dumps(results))
        ''')

        exec_result = self.execute_script(wrapper_code)

        if not exec_result.success:
            # Return all samples as errors
            return [
                CleanerResult(
                    sample=sample,
                    is_target=False,
                    error=exec_result.stderr,
                )
                for sample in samples
            ]

        # Parse results
        try:
            parsed_results = json.loads(exec_result.stdout.strip())
        except json.JSONDecodeError:
            return [
                CleanerResult(
                    sample=sample,
                    is_target=False,
                    error=f"Failed to parse cleaner output: {exec_result.stdout}",
                )
                for sample in samples
            ]

        # Map results back to samples
        cleaner_results = []
        for sample, result in zip(samples, parsed_results):
            cleaner_results.append(
                CleanerResult(
                    sample=sample,
                    is_target=result.get("is_target", False),
                    error=result.get("error"),
                )
            )

        return cleaner_results
