"""Main orchestrator engine - manages the evolution pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from evoscripts.agents.code_agent import CodeAgent
from evoscripts.agents.judge_agent import JudgeAgent
from evoscripts.config import settings
from evoscripts.orchestrator.sampler import Sampler
from evoscripts.orchestrator.state import (
    EvaluationReport,
    PipelineState,
    RunContext,
)
from evoscripts.sandbox.executor import SandboxExecutor

if TYPE_CHECKING:
    from evoscripts.templates import TemplateBundle

console = Console()


class EvoEngine:
    """Main orchestrator for the evolution pipeline."""

    def __init__(
        self,
        data_path: str,
        requirement: str,
        template_bundle: TemplateBundle | None = None,
    ):
        """Initialize the evolution engine.

        Args:
            data_path: Path to the JSONL data file.
            requirement: Natural language cleaning requirements.
            template_bundle: Optional template bundle with code/examples.
        """
        self.context = RunContext(
            data_path=data_path,
            requirement=requirement,
            template_bundle=template_bundle,
        )

        self.sampler = Sampler(data_path)
        self.code_agent = CodeAgent()
        self.judge_agent = JudgeAgent()
        self.executor = SandboxExecutor()

    def run(self) -> str | None:
        """Run the complete evolution pipeline.

        Returns:
            The final cleaner script if successful, None otherwise.
        """
        console.print(Panel.fit(
            f"[bold blue]EvoScripts Pipeline[/]\n"
            f"Data: {self.context.data_path}\n"
            f"Total samples: {self.sampler.total_count}",
            title="Starting",
        ))

        try:
            # Phase 1: Taste Alignment
            self._phase_taste_alignment()

            # Phase 2: Evolution Loop
            self._phase_evolution_loop()

            return self.context.current_script

        except KeyboardInterrupt:
            console.print("\n[yellow]Pipeline interrupted by user.[/]")
            return self.context.current_script

        except Exception as e:
            console.print(f"[red]Pipeline failed: {e}[/]")
            self.context.state = PipelineState.FAILED
            self.context.last_error = str(e)
            raise

    def _phase_taste_alignment(self) -> None:
        """Phase 1: Align evaluation criteria with human expectations."""
        self.context.state = PipelineState.TASTE_ALIGNMENT
        console.print("\n[bold cyan]Phase 1: Taste Alignment[/]")

        # Sample a few items for rubric drafting
        taste_samples = self.sampler.sample(settings.taste_sample_size)
        sample_data = self.sampler.get_sample_data(taste_samples)

        console.print(f"Sampled {len(taste_samples)} items for taste alignment.")

        # Draft initial rubric
        console.print("Drafting evaluation rubric...")
        rubric = self.judge_agent.draft_rubric(
            requirement=self.context.requirement,
            samples=sample_data,
            template_bundle=self.context.template_bundle,
        )

        # Display rubric for human review
        console.print(Panel(rubric, title="[bold]Draft Rubric[/]", border_style="green"))

        # HITL: Ask for confirmation or refinement
        while True:
            action = Prompt.ask(
                "Action",
                choices=["approve", "refine", "abort"],
                default="approve",
            )

            if action == "approve":
                self.context.lock_rubric(rubric)
                console.print("[green]Rubric locked.[/]")
                break

            elif action == "refine":
                feedback = Prompt.ask("Enter your feedback")
                rubric = self.judge_agent.refine_rubric(rubric, feedback)
                console.print(Panel(rubric, title="[bold]Refined Rubric[/]", border_style="green"))

            elif action == "abort":
                raise KeyboardInterrupt("User aborted during taste alignment.")

    def _phase_evolution_loop(self) -> None:
        """Phase 2: Iteratively evolve the cleaner script."""
        self.context.state = PipelineState.EVOLUTION_LOOP
        console.print("\n[bold cyan]Phase 2: Evolution Loop[/]")

        # Generate initial script
        console.print("Generating initial cleaner script...")
        initial_samples = self.sampler.sample(settings.evolution_sample_size)
        sample_data = self.sampler.get_sample_data(initial_samples)

        script = self.code_agent.generate_cleaner(
            requirement=self.context.requirement,
            rubric=self.context.rubric,
            samples=sample_data,
            template_bundle=self.context.template_bundle,
        )

        # Validate and fix syntax if needed
        script = self._ensure_valid_syntax(script)
        self.context.update_script(script)

        console.print(f"[dim]Script v{self.context.script_version} generated.[/]")

        # Evolution loop
        while self.context.iteration < settings.max_iterations:
            console.print(f"\n[bold]Iteration {self.context.iteration + 1}[/]")

            # Sample and run cleaner
            samples = self.sampler.sample(settings.evolution_sample_size)
            console.print(f"Testing on {len(samples)} samples...")

            results = self.executor.run_cleaner_on_samples(
                self.context.current_script,
                samples,
            )

            # Check for execution errors
            errors = [r for r in results if r.error]
            if errors:
                console.print(f"[yellow]Found {len(errors)} execution errors. Fixing...[/]")
                script = self.code_agent.fix_syntax_error(
                    self.context.current_script,
                    errors[0].error,
                )
                script = self._ensure_valid_syntax(script)
                self.context.update_script(script)
                continue

            # Evaluate results
            target_count = sum(1 for r in results if r.is_target)
            console.print(
                f"Cleaner marked {target_count}/{len(results)} as target data."
            )

            # Check for low recall warning
            if target_count == 0:
                console.print(
                    "[red]Warning: No target data found! Rules may be too strict.[/]"
                )
                # Force refinement with this feedback
                bad_cases = []  # No specific bad cases, just too strict
                script = self.code_agent.refine_cleaner(
                    self.context.current_script,
                    bad_cases,
                    self.context.rubric + "\n\nIMPORTANT: Current rules are too strict. "
                    "Please relax the criteria to capture more target data.",
                )
                script = self._ensure_valid_syntax(script)
                self.context.update_script(script)
                continue

            # Judge evaluation
            console.print("Evaluating with Judge...")
            report = self.judge_agent.evaluate_batch(
                rubric=self.context.rubric,
                results=results,
            )
            self.context.record_evaluation(report)

            # Display metrics
            self._display_metrics(report)

            # Check exit condition
            if self._check_exit_condition(report):
                self.context.state = PipelineState.COMPLETED
                console.print("\n[bold green]Target precision achieved![/]")
                break

            # HITL checkpoint
            if self.context.iteration % settings.hitl_interval == 0:
                if not self._hitl_checkpoint():
                    break

            # Refine based on bad cases
            bad_cases = report.get_bad_cases()
            if bad_cases:
                console.print(f"Refining script based on {len(bad_cases)} bad cases...")
                script = self.code_agent.refine_cleaner(
                    self.context.current_script,
                    bad_cases,
                    self.context.rubric,
                )
                script = self._ensure_valid_syntax(script)
                self.context.update_script(script)
                console.print(f"[dim]Script v{self.context.script_version} generated.[/]")

        if self.context.iteration >= settings.max_iterations:
            console.print(
                f"[yellow]Reached max iterations ({settings.max_iterations}). "
                "Stopping with current best script.[/]"
            )

    def _ensure_valid_syntax(self, code: str, max_attempts: int = 3) -> str:
        """Ensure the code has valid syntax, fixing if necessary."""
        for attempt in range(max_attempts):
            is_valid, error = self.executor.validate_syntax(code)
            if is_valid:
                return code

            console.print(f"[yellow]Syntax error (attempt {attempt + 1}): {error}[/]")
            code = self.code_agent.fix_syntax_error(code, error)

        raise RuntimeError("Failed to generate syntactically valid code after multiple attempts.")

    def _check_exit_condition(self, report: EvaluationReport) -> bool:
        """Check if the exit condition is met."""
        return report.precision >= settings.precision_threshold

    def _display_metrics(self, report: EvaluationReport) -> None:
        """Display evaluation metrics."""
        console.print(
            f"  Precision: [{'green' if report.precision >= settings.precision_threshold else 'yellow'}]"
            f"{report.precision:.1%}[/] "
            f"(TP={report.true_positives}, FP={report.false_positives})"
        )
        console.print(
            f"  Recall: {report.recall:.1%} "
            f"(TP={report.true_positives}, FN={report.false_negatives})"
        )

    def _hitl_checkpoint(self) -> bool:
        """Human-in-the-loop checkpoint. Returns True to continue, False to stop."""
        self.context.state = PipelineState.HITL_PAUSE

        console.print("\n[bold yellow]HITL Checkpoint[/]")
        console.print(f"Current iteration: {self.context.iteration}")
        console.print(f"Script version: {self.context.script_version}")

        if self.context.evaluation_history:
            latest = self.context.evaluation_history[-1]
            console.print(f"Latest precision: {latest.precision:.1%}")

        should_continue = Confirm.ask("Continue evolution?", default=True)
        self.context.state = PipelineState.EVOLUTION_LOOP

        return should_continue
