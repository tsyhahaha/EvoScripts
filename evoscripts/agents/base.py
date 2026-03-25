"""Base agent class for LLM interactions."""

from abc import ABC, abstractmethod
from typing import Any

from evoscripts.config import settings


class BaseAgent(ABC):
    """Abstract base class for all LLM agents."""

    def __init__(self, model: str | None = None):
        """Initialize the agent with a specific model.

        Args:
            model: Model identifier. If None, uses default from settings.
        """
        self.model = model or self._default_model()
        self._client: Any = None

    @abstractmethod
    def _default_model(self) -> str:
        """Return the default model for this agent type."""
        ...

    @abstractmethod
    def _init_client(self) -> Any:
        """Initialize and return the LLM client."""
        ...

    @property
    def client(self) -> Any:
        """Lazy-initialize and return the LLM client."""
        if self._client is None:
            self._client = self._init_client()
        return self._client

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from markdown code blocks.

        Args:
            text: LLM response that may contain code blocks.

        Returns:
            Extracted code or the original text if no code block found.
        """
        import re

        # Try to find Python code block
        pattern = r"```(?:python)?\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            # Return the longest code block (usually the main implementation)
            return max(matches, key=len).strip()

        return text.strip()

    def _format_samples_for_prompt(self, samples: list[dict[str, Any]]) -> str:
        """Format samples for inclusion in prompts.

        Args:
            samples: List of sample data dictionaries.

        Returns:
            Formatted string representation of samples.
        """
        import json

        lines = []
        for i, sample in enumerate(samples, 1):
            lines.append(f"=== Sample {i} ===")
            lines.append(json.dumps(sample, ensure_ascii=False, indent=2))
            lines.append("")
        return "\n".join(lines)
