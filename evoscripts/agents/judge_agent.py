"""Judge Agent - evaluates cleaner results using GPT-4o."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import openai

from evoscripts.agents.base import BaseAgent
from evoscripts.config import settings
from evoscripts.orchestrator.state import (
    CleanerResult,
    EvaluationReport,
    JudgeVerdict,
    Verdict,
)
from evoscripts.prompts.judge import JUDGE_PROMPTS

if TYPE_CHECKING:
    from evoscripts.templates import TemplateBundle


class JudgeAgent(BaseAgent):
    """Agent for evaluating data cleaning results and generating rubrics."""

    def _default_model(self) -> str:
        return settings.judge_model

    def _init_client(self) -> openai.OpenAI:
        return openai.OpenAI(api_key=settings.openai_api_key)

    def draft_rubric(
        self,
        requirement: str,
        samples: list[dict],
        template_bundle: TemplateBundle | None = None,
    ) -> str:
        """Draft an initial evaluation rubric based on requirements.

        Args:
            requirement: Natural language cleaning requirements.
            samples: Example data samples.
            template_bundle: Optional template bundle with examples.

        Returns:
            A structured rubric as a string.
        """
        samples_str = self._format_samples_for_prompt(samples)

        # Format templates (especially target/non-target examples)
        templates_str = (
            template_bundle.format_for_prompt()
            if template_bundle
            else "No reference examples provided."
        )

        user_prompt = JUDGE_PROMPTS["draft_rubric"].format(
            requirement=requirement,
            samples=samples_str,
            templates=templates_str,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": JUDGE_PROMPTS["system"]},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content

    def evaluate_batch(
        self,
        rubric: str,
        results: list[CleanerResult],
    ) -> EvaluationReport:
        """Evaluate a batch of cleaner results against the rubric.

        Args:
            rubric: The locked evaluation rubric.
            results: List of cleaner results to evaluate.

        Returns:
            An EvaluationReport with verdicts and statistics.
        """
        verdicts = []

        for result in results:
            verdict = self._evaluate_single(rubric, result)
            verdicts.append(verdict)

        # Calculate statistics
        report = EvaluationReport(
            verdicts=verdicts,
            total_samples=len(results),
        )

        for v in verdicts:
            if v.is_target_prediction:
                if v.verdict == Verdict.GOOD:
                    report.true_positives += 1
                else:
                    report.false_positives += 1
                    v.is_false_positive = True
            else:
                if v.verdict == Verdict.GOOD:
                    report.true_negatives += 1
                else:
                    report.false_negatives += 1
                    v.is_false_negative = True

        return report

    def _evaluate_single(
        self,
        rubric: str,
        result: CleanerResult,
    ) -> JudgeVerdict:
        """Evaluate a single cleaner result.

        Args:
            rubric: The evaluation rubric.
            result: A single cleaner result.

        Returns:
            A JudgeVerdict for this result.
        """
        sample_data = json.dumps(result.sample.data, ensure_ascii=False, indent=2)
        prediction = "TARGET" if result.is_target else "NON-TARGET"

        user_prompt = JUDGE_PROMPTS["evaluate_single"].format(
            rubric=rubric,
            sample_data=sample_data,
            prediction=prediction,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": JUDGE_PROMPTS["system"]},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Parse JSON response
        response_text = response.choices[0].message.content
        parsed = json.loads(response_text)

        verdict_str = parsed.get("verdict", "uncertain").lower()
        verdict = Verdict.GOOD if verdict_str == "good" else (
            Verdict.BAD if verdict_str == "bad" else Verdict.UNCERTAIN
        )

        return JudgeVerdict(
            sample_index=result.sample.index,
            verdict=verdict,
            is_target_prediction=result.is_target,
            reasoning=parsed.get("reasoning", "No reasoning provided."),
        )

    def refine_rubric(
        self,
        rubric: str,
        feedback: str,
    ) -> str:
        """Refine the rubric based on human feedback.

        Args:
            rubric: Current rubric.
            feedback: Human feedback for refinement.

        Returns:
            Refined rubric.
        """
        user_prompt = JUDGE_PROMPTS["refine_rubric"].format(
            rubric=rubric,
            feedback=feedback,
        )

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": JUDGE_PROMPTS["system"]},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content
