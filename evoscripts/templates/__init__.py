"""Template loading and management."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodeTemplate:
    """A code template with metadata."""

    name: str
    path: Path
    content: str
    description: str = ""


@dataclass
class DataExample:
    """An example data sample."""

    name: str
    path: Path
    data: dict | list
    is_target: bool  # True for target examples, False for non-target


@dataclass
class OutputFormat:
    """Output format specification."""

    name: str
    path: Path
    content: dict | list | str
    is_schema: bool = False


@dataclass
class TemplateBundle:
    """Collection of all templates and examples."""

    code_templates: list[CodeTemplate] = field(default_factory=list)
    target_examples: list[DataExample] = field(default_factory=list)
    non_target_examples: list[DataExample] = field(default_factory=list)
    output_formats: list[OutputFormat] = field(default_factory=list)

    @property
    def has_code_templates(self) -> bool:
        return len(self.code_templates) > 0

    @property
    def has_examples(self) -> bool:
        return len(self.target_examples) > 0 or len(self.non_target_examples) > 0

    @property
    def has_output_format(self) -> bool:
        return len(self.output_formats) > 0

    def format_for_prompt(self) -> str:
        """Format all templates for inclusion in prompts."""
        sections = []

        # Code templates
        if self.code_templates:
            sections.append("### Code Templates (Reference Patterns)")
            for tmpl in self.code_templates:
                sections.append(f"\n#### {tmpl.name}")
                if tmpl.description:
                    sections.append(f"_{tmpl.description}_")
                sections.append(f"```python\n{tmpl.content}\n```")

        # Target examples
        if self.target_examples:
            sections.append("\n### Target Data Examples (SHOULD be selected)")
            for ex in self.target_examples:
                sections.append(f"\n#### {ex.name}")
                sections.append(f"```json\n{json.dumps(ex.data, ensure_ascii=False, indent=2)}\n```")

        # Non-target examples
        if self.non_target_examples:
            sections.append("\n### Non-Target Data Examples (should be FILTERED OUT)")
            for ex in self.non_target_examples:
                sections.append(f"\n#### {ex.name}")
                sections.append(f"```json\n{json.dumps(ex.data, ensure_ascii=False, indent=2)}\n```")

        # Output format
        if self.output_formats:
            sections.append("\n### Expected Output Format")
            for fmt in self.output_formats:
                sections.append(f"\n#### {fmt.name}")
                if fmt.is_schema:
                    sections.append("_(JSON Schema)_")
                if isinstance(fmt.content, (dict, list)):
                    sections.append(f"```json\n{json.dumps(fmt.content, ensure_ascii=False, indent=2)}\n```")
                else:
                    sections.append(f"```\n{fmt.content}\n```")

        return "\n".join(sections) if sections else "No templates provided."


class TemplateLoader:
    """Load and organize templates from a template directory."""

    def __init__(self, template_dir: str | Path):
        """Initialize the template loader.

        Args:
            template_dir: Path to the templates directory.
        """
        self.template_dir = Path(template_dir)

        if not self.template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

    def load(self) -> TemplateBundle:
        """Load all templates from the directory.

        Returns:
            A TemplateBundle containing all loaded templates.
        """
        bundle = TemplateBundle()

        # Load code templates
        code_dir = self.template_dir / "code"
        if code_dir.exists():
            bundle.code_templates = self._load_code_templates(code_dir)

        # Load examples
        examples_dir = self.template_dir / "examples"
        if examples_dir.exists():
            target_dir = examples_dir / "target"
            non_target_dir = examples_dir / "non_target"

            if target_dir.exists():
                bundle.target_examples = self._load_examples(target_dir, is_target=True)
            if non_target_dir.exists():
                bundle.non_target_examples = self._load_examples(non_target_dir, is_target=False)

        # Load output formats
        output_dir = self.template_dir / "output"
        if output_dir.exists():
            bundle.output_formats = self._load_output_formats(output_dir)

        return bundle

    def _load_code_templates(self, code_dir: Path) -> list[CodeTemplate]:
        """Load Python code templates."""
        templates = []

        for py_file in code_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")

            # Try to extract docstring as description
            description = self._extract_module_docstring(content)

            templates.append(CodeTemplate(
                name=py_file.stem,
                path=py_file,
                content=content,
                description=description,
            ))

        return templates

    def _load_examples(self, examples_dir: Path, is_target: bool) -> list[DataExample]:
        """Load example data files."""
        examples = []

        # Load .json files
        for json_file in examples_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                examples.append(DataExample(
                    name=json_file.stem,
                    path=json_file,
                    data=data,
                    is_target=is_target,
                ))
            except json.JSONDecodeError:
                continue

        # Load .jsonl files (take first few lines)
        for jsonl_file in examples_dir.glob("*.jsonl"):
            try:
                lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
                # Take up to 3 examples from each jsonl file
                for i, line in enumerate(lines[:3]):
                    if line.strip():
                        data = json.loads(line)
                        examples.append(DataExample(
                            name=f"{jsonl_file.stem}_{i+1}",
                            path=jsonl_file,
                            data=data,
                            is_target=is_target,
                        ))
            except (json.JSONDecodeError, IndexError):
                continue

        return examples

    def _load_output_formats(self, output_dir: Path) -> list[OutputFormat]:
        """Load output format specifications."""
        formats = []

        for json_file in output_dir.glob("*.json"):
            try:
                content = json.loads(json_file.read_text(encoding="utf-8"))
                is_schema = ".schema" in json_file.name or "$schema" in content

                formats.append(OutputFormat(
                    name=json_file.stem,
                    path=json_file,
                    content=content,
                    is_schema=is_schema,
                ))
            except json.JSONDecodeError:
                continue

        return formats

    def _extract_module_docstring(self, content: str) -> str:
        """Extract the module-level docstring from Python code."""
        import ast

        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            return docstring or ""
        except SyntaxError:
            return ""
