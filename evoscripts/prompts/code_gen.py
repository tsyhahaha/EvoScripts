"""Prompts for the Code Agent."""

CODE_GEN_PROMPTS = {
    "system": """You are an expert Python developer specializing in data cleaning and ETL scripts.
Your task is to write Python functions that filter and classify JSONL data.

Guidelines:
1. Write clean, efficient, and well-documented code
2. The main function must be named `is_target(data: dict) -> bool`
3. Return True if the data matches the target criteria, False otherwise
4. Handle edge cases gracefully (missing keys, unexpected types, etc.)
5. Do not use external libraries beyond Python standard library
6. Focus on precision - it's better to miss some targets than to include non-targets

When reference templates are provided:
- Follow the coding patterns and style from the code templates
- Use the target/non-target examples to understand the classification boundary
- Match the output format if specified

Output only the Python code wrapped in ```python``` code blocks.""",

    "generate": """Based on the following requirements, write a Python function to classify JSONL data.

## Cleaning Requirements
{requirement}

## Evaluation Rubric (criteria for what counts as "target" data)
{rubric}

## Random Data Samples (from the actual dataset)
{samples}

## Reference Templates and Examples
{templates}

IMPORTANT:
- If code templates are provided, follow their patterns and style
- If target/non-target examples are provided, use them to understand the exact classification criteria
- The target examples show data that SHOULD return True
- The non-target examples show data that SHOULD return False

Write a Python function `is_target(data: dict) -> bool` that returns True for data matching the target criteria.
Include any helper functions as needed.""",

    "fix_syntax": """The following Python code has syntax errors. Fix them while preserving the logic.

## Code with Errors
```python
{code}
```

## Error Message
{error}

Return the fixed Python code.""",

    "refine": """The current cleaner script has some issues. Refine it based on the bad cases below.

## Current Script
```python
{code}
```

## Bad Cases (misclassified samples)
{bad_cases}

## Evaluation Rubric
{rubric}

Analyze the bad cases and modify the script to fix these issues.
Return the complete refined Python code.""",
}
