"""CLI entry point for EvoScripts."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from evoscripts import __version__
from evoscripts.config import settings
from evoscripts.orchestrator.engine import EvoEngine
from evoscripts.templates import TemplateLoader

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """EvoScripts - Automated JSONL data cleaning script generator."""
    pass


@main.command()
@click.argument("data_path", type=click.Path(exists=True))
@click.argument("requirement")
@click.option(
    "--templates",
    "-t",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to templates directory (containing code/, examples/, output/)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output path for the generated script",
)
@click.option(
    "--precision",
    "-p",
    type=float,
    default=0.9,
    help="Target precision threshold (default: 0.9)",
)
@click.option(
    "--max-iterations",
    "-n",
    type=int,
    default=10,
    help="Maximum evolution iterations (default: 10)",
)
def evolve(
    data_path: str,
    requirement: str,
    templates: str | None,
    output: str | None,
    precision: float,
    max_iterations: int,
):
    """Run the evolution pipeline to generate a cleaner script.

    DATA_PATH: Path to the JSONL data file.
    REQUIREMENT: Natural language description of cleaning requirements.

    Example:
        evoscripts evolve data.jsonl "Filter out incomplete records"
        evoscripts evolve data.jsonl "提取多轮对话" --templates ./templates
    """
    # Update settings
    settings.precision_threshold = precision
    settings.max_iterations = max_iterations

    # Load templates if provided
    template_bundle = None
    if templates:
        try:
            loader = TemplateLoader(templates)
            template_bundle = loader.load()
            console.print(f"[green]Loaded templates from: {templates}[/]")

            # Show what was loaded
            if template_bundle.code_templates:
                console.print(f"  Code templates: {len(template_bundle.code_templates)}")
            if template_bundle.target_examples:
                console.print(f"  Target examples: {len(template_bundle.target_examples)}")
            if template_bundle.non_target_examples:
                console.print(f"  Non-target examples: {len(template_bundle.non_target_examples)}")
            if template_bundle.output_formats:
                console.print(f"  Output formats: {len(template_bundle.output_formats)}")
        except FileNotFoundError as e:
            console.print(f"[red]Error loading templates: {e}[/]")
            return

    # Run the pipeline
    engine = EvoEngine(
        data_path=data_path,
        requirement=requirement,
        template_bundle=template_bundle,
    )

    final_script = engine.run()

    if final_script:
        console.print("\n[bold green]Final Script:[/]")
        syntax = Syntax(final_script, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax))

        # Save if output path specified
        if output:
            Path(output).write_text(final_script, encoding="utf-8")
            console.print(f"\n[green]Script saved to: {output}[/]")
        else:
            # Default output path
            default_output = "cleaner_final.py"
            Path(default_output).write_text(final_script, encoding="utf-8")
            console.print(f"\n[green]Script saved to: {default_output}[/]")


@main.command()
@click.argument("data_path", type=click.Path(exists=True))
@click.option(
    "--count",
    "-n",
    type=int,
    default=5,
    help="Number of samples to display",
)
def preview(data_path: str, count: int):
    """Preview samples from a JSONL file.

    DATA_PATH: Path to the JSONL data file.
    """
    from evoscripts.orchestrator.sampler import Sampler
    import json

    sampler = Sampler(data_path)
    samples = sampler.sample(count)

    console.print(f"[bold]Previewing {len(samples)} samples from {data_path}[/]\n")

    for sample in samples:
        console.print(f"[dim]--- Sample {sample.index} ---[/]")
        formatted = json.dumps(sample.data, ensure_ascii=False, indent=2)
        console.print(formatted)
        console.print()


@main.command()
@click.argument("script_path", type=click.Path(exists=True))
@click.argument("data_path", type=click.Path(exists=True))
@click.option(
    "--count",
    "-n",
    type=int,
    default=10,
    help="Number of samples to test",
)
def test(script_path: str, data_path: str, count: int):
    """Test a cleaner script on sample data.

    SCRIPT_PATH: Path to the cleaner script.
    DATA_PATH: Path to the JSONL data file.
    """
    from evoscripts.orchestrator.sampler import Sampler
    from evoscripts.sandbox.executor import SandboxExecutor

    script = Path(script_path).read_text(encoding="utf-8")
    sampler = Sampler(data_path)
    executor = SandboxExecutor()

    samples = sampler.sample(count)
    results = executor.run_cleaner_on_samples(script, samples)

    console.print(f"[bold]Testing {script_path} on {len(samples)} samples[/]\n")

    target_count = 0
    error_count = 0

    for result in results:
        if result.error:
            console.print(f"[red]Sample {result.sample.index}: ERROR - {result.error}[/]")
            error_count += 1
        elif result.is_target:
            console.print(f"[green]Sample {result.sample.index}: TARGET[/]")
            target_count += 1
        else:
            console.print(f"[dim]Sample {result.sample.index}: non-target[/]")

    console.print(f"\n[bold]Summary:[/]")
    console.print(f"  Target: {target_count}/{len(samples)}")
    console.print(f"  Errors: {error_count}/{len(samples)}")


@main.command()
def config():
    """Display current configuration."""
    console.print("[bold]Current Configuration[/]\n")

    config_items = [
        ("Code Agent Model", settings.code_agent_model),
        ("Judge Model", settings.judge_model),
        ("Taste Sample Size", settings.taste_sample_size),
        ("Evolution Sample Size", settings.evolution_sample_size),
        ("Precision Threshold", f"{settings.precision_threshold:.0%}"),
        ("Max Iterations", settings.max_iterations),
        ("HITL Interval", settings.hitl_interval),
        ("Sandbox Timeout", f"{settings.sandbox_timeout}s"),
    ]

    for name, value in config_items:
        console.print(f"  {name}: [cyan]{value}[/]")

    # Check API keys
    console.print("\n[bold]API Keys:[/]")
    console.print(f"  Anthropic: {'[green]configured[/]' if settings.anthropic_api_key else '[red]missing[/]'}")
    console.print(f"  OpenAI: {'[green]configured[/]' if settings.openai_api_key else '[red]missing[/]'}")


if __name__ == "__main__":
    main()
