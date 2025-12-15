"""
Base class for pipeline stages
"""
from abc import ABC, abstractmethod
from typing import List, Any
from pathlib import Path
import subprocess
import json

from ..utils.logger import get_logger


class PipelineStage(ABC):
    """Abstract base class for pipeline stages"""

    def __init__(self, binary_path: Path):
        """
        Initialize pipeline stage

        Args:
            binary_path: Path to the tool binary
        """
        self.binary_path = Path(binary_path)
        self.logger = get_logger(self.__class__.__name__)

        # Verify binary exists
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the pipeline stage"""
        pass

    def run_command(self,
                    args: List[str],
                    input_data: str = None,
                    timeout: int = 300) -> subprocess.CompletedProcess:
        """
        Run a command with the tool binary

        Args:
            args: Command arguments
            input_data: Optional stdin input
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess object
        """
        cmd = [str(self.binary_path)] + args

        self.logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit
            )

            if result.returncode != 0:
                self.logger.warning(
                    f"Command returned non-zero exit code: {result.returncode}"
                )
                if result.stderr:
                    self.logger.debug(f"stderr: {result.stderr}")

            return result

        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s")
            raise
        except Exception as e:
            self.logger.error(f"Command execution failed: {str(e)}")
            raise

    def parse_json_lines(self, output: str) -> List[dict]:
        """
        Parse JSON Lines (JSONL) output

        Args:
            output: JSONL string

        Returns:
            List of parsed JSON objects
        """
        results = []

        for line in output.strip().split('\n'):
            if not line.strip():
                continue

            try:
                obj = json.loads(line)
                results.append(obj)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON line: {e}")
                continue

        return results
