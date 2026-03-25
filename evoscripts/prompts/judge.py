"""Prompts for the Judge Agent."""

JUDGE_PROMPTS = {
    "system": """You are an expert data quality evaluator. Your role is to:
1. Create clear evaluation rubrics for data classification tasks
2. Objectively judge whether data samples match specified criteria
3. Provide detailed reasoning for your judgments

Be strict and consistent. When in doubt, err on the side of caution.""",

    "draft_rubric": """Based on the following cleaning requirements and sample data, create a structured evaluation rubric.

## Cleaning Requirements
{requirement}

## Random Data Samples (from the actual dataset)
{samples}

## Reference Templates and Examples (if provided)
{templates}

Create a rubric with the following structure:
1. **Target Data Definition**: Clear criteria for what constitutes "target" data
2. **Non-Target Data Definition**: Clear criteria for what should be excluded
3. **Edge Cases**: How to handle ambiguous cases
4. **Quality Checks**: Specific fields or patterns to verify

IMPORTANT:
- If target/non-target examples are provided above, use them as ground truth references
- The rubric must be consistent with the provided examples
- Be specific about field names, value patterns, and structural requirements

The rubric should be precise enough that another evaluator would reach the same conclusions.""",

    "evaluate_single": """Evaluate whether the cleaner's prediction for this sample is correct.

## Evaluation Rubric
{rubric}

## Sample Data
{sample_data}

## Cleaner's Prediction
The cleaner marked this sample as: {prediction}

Evaluate whether this prediction is correct according to the rubric.

Respond in JSON format:
{{
    "verdict": "good" or "bad",
    "reasoning": "Brief explanation of why the prediction is correct or incorrect"
}}

- "good" means the prediction matches the rubric criteria
- "bad" means the prediction contradicts the rubric criteria""",

    "refine_rubric": """Refine the evaluation rubric based on human feedback.

## Current Rubric
{rubric}

## Human Feedback
{feedback}

Update the rubric to incorporate this feedback while maintaining its structure and clarity.
Output the complete refined rubric.""",
}
