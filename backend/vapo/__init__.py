"""
VAPO (Vertex AI Prompt Optimizer) Integration Module

This module provides tools for optimizing prompts using Google's Vertex AI Prompt Optimizer.
It supports both zero-shot optimization (no data required) and data-driven optimization
(requires evaluation datasets).

Usage:
    from vapo import VAPOClient

    client = VAPOClient(project_id="your-project", location="us-central1")

    # Zero-shot optimization
    result = client.optimize_zero_shot(prompt="Your prompt here")
    print(result["suggested_prompt"])

    # Data-driven optimization (requires dataset)
    result = client.optimize_data_driven(
        system_instruction="Your system prompt",
        prompt_template="Your user prompt template",
        dataset_uri="gs://bucket/dataset.jsonl"
    )
"""

from .vapo_client import VAPOClient

__all__ = ["VAPOClient"]
