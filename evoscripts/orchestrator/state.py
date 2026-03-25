"""Pipeline state definitions and data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from evoscripts.templates import TemplateBundle


class PipelineState(Enum):
    """States of the evolution pipeline."""

    INIT = "init"
    TASTE_ALIGNMENT = "taste_alignment"
    RUBRIC_LOCKED = "rubric_locked"
    EVOLUTION_LOOP = "evolution_loop"
    HITL_PAUSE = "hitl_pause"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(Enum):
    """Judge verdict for a sample."""

    GOOD = "good"
    BAD = "bad"
    UNCERTAIN = "uncertain"


@dataclass
class Sample:
    """A single data sample from the JSONL file."""

    index: int
    data: dict[str, Any]
    raw_line: str

    def __repr__(self) -> str:
        return f"Sample(index={self.index}, keys={list(self.data.keys())})"


@dataclass
class CleanerResult:
    """Result of running the cleaner script on a sample."""

    sample: Sample
    is_target: bool  # True if cleaner marked this as target data
    output: dict[str, Any] | None = None  # Cleaned/transformed output if any
    error: str | None = None


@dataclass
class JudgeVerdict:
    """Judge's verdict on a single cleaner result."""

    sample_index: int
    verdict: Verdict
    is_target_prediction: bool  # What the cleaner predicted
    reasoning: str
    is_false_positive: bool = False  # Predicted target but actually non-target
    is_false_negative: bool = False  # Predicted non-target but actually target


@dataclass
class EvaluationReport:
    """Summary of judge evaluation on a batch."""

    verdicts: list[JudgeVerdict]
    total_samples: int
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)."""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)."""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """F1 = 2 * (Precision * Recall) / (Precision + Recall)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def get_bad_cases(self) -> list[JudgeVerdict]:
        """Return all false positive and false negative cases."""
        return [v for v in self.verdicts if v.is_false_positive or v.is_false_negative]


@dataclass
class RunContext:
    """Mutable context holding the state of a pipeline run."""

    # Input
    data_path: str
    requirement: str
    template_bundle: TemplateBundle | None = None

    # State
    state: PipelineState = PipelineState.INIT
    iteration: int = 0

    # Artifacts
    rubric: str | None = None
    rubric_locked: bool = False
    current_script: str | None = None
    script_version: int = 0

    # History
    evaluation_history: list[EvaluationReport] = field(default_factory=list)
    script_history: list[str] = field(default_factory=list)

    # Errors
    last_error: str | None = None

    def lock_rubric(self, rubric: str) -> None:
        """Lock the rubric after human confirmation."""
        self.rubric = rubric
        self.rubric_locked = True
        self.state = PipelineState.RUBRIC_LOCKED

    def update_script(self, script: str) -> None:
        """Update the current cleaner script."""
        if self.current_script:
            self.script_history.append(self.current_script)
        self.current_script = script
        self.script_version += 1

    def record_evaluation(self, report: EvaluationReport) -> None:
        """Record an evaluation report."""
        self.evaluation_history.append(report)
        self.iteration += 1
