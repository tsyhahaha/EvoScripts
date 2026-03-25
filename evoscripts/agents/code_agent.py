"""Code Agent - generates and refines data cleaning scripts using Claude."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anthropic

from evoscripts.agents.base import BaseAgent
from evoscripts.config import settings
from evoscripts.orchestrator.state import JudgeVerdict
from evoscripts.prompts.code_gen import CODE_GEN_PROMPTS

if TYPE_CHECKING:
    from evoscripts.templates import TemplateBundle


class CodeAgent(BaseAgent):
    """Agent for generating and refining Python data cleaning scripts."""

    def _default_model(self) -> str:
        return settings.code_agent_model

    def _init_client(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate_cleaner(
        self,
        requirement: str,
        rubric: str,
        samples: list[dict],
        template_bundle: TemplateBundle | None = None,
    ) -> str:
        """Generate initial cleaner script.

        Args:
            requirement: Natural language description of cleaning requirements.
            rubric: The locked evaluation rubric.
            samples: Example data samples for context.
            template_bundle: Optional template bundle with code/examples.

        Returns:
            Generated Python script as a string.
        """
        samples_str = self._format_samples_for_prompt(samples)

        # Format templates
        templates_str = (
            template_bundle.format_for_prompt()
            if template_bundle
            else "No templates provided."
        )

        user_prompt = CODE_GEN_PROMPTS["generate"].format(
            requirement=requirement,
            rubric=rubric,
            samples=samples_str,
            templates=templates_str,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=CODE_GEN_PROMPTS["system"],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return self._extract_code_block(response.content[0].text)

    def fix_syntax_error(self, code: str, error: str) -> str:
        """Fix syntax errors in the generated script.

        Args:
            code: The script with syntax errors.
            error: The error traceback.

        Returns:
            Fixed Python script.
        """
        user_prompt = CODE_GEN_PROMPTS["fix_syntax"].format(
            code=code,
            error=error,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=CODE_GEN_PROMPTS["system"],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return self._extract_code_block(response.content[0].text)

    def refine_cleaner(
        self,
        code: str,
        bad_cases: list[JudgeVerdict],
        rubric: str,
    ) -> str:
        """Refine the cleaner script based on bad cases.

        Args:
            code: Current cleaner script.
            bad_cases: List of false positive/negative verdicts.
            rubric: The evaluation rubric for context.

        Returns:
            Refined Python script.
        """
        # Format bad cases for the prompt
        bad_cases_str = self._format_bad_cases(bad_cases)

        user_prompt = CODE_GEN_PROMPTS["refine"].format(
            code=code,
            bad_cases=bad_cases_str,
            rubric=rubric,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=CODE_GEN_PROMPTS["system"],
            messages=[{"role": "user", "content": user_prompt}],
        )

        return self._extract_code_block(response.content[0].text)

    def _format_bad_cases(self, bad_cases: list[JudgeVerdict]) -> str:
        """Format bad cases for inclusion in prompts."""
        lines = []
        for case in bad_cases:
            case_type = "FALSE POSITIVE" if case.is_false_positive else "FALSE NEGATIVE"
            lines.append(f"=== {case_type} (Sample {case.sample_index}) ===")
            lines.append(f"Prediction: {'Target' if case.is_target_prediction else 'Non-target'}")
            lines.append(f"Reasoning: {case.reasoning}")
            lines.append("")
        return "\n".join(lines) if lines else "No bad cases."
