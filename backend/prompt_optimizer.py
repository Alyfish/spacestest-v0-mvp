"""
Vertex AI Prompt Optimizer Integration

This module provides Zero-Shot prompt optimization using Vertex AI.
It wraps the Vertex AI SDK to optimize system prompts and user templates.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

import vertexai
from vertexai import types

from config import VAPO_CONFIG

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """
    Zero-Shot Prompt Optimizer using Vertex AI.

    Usage:
        optimizer = PromptOptimizer()
        result = optimizer.optimize_prompt("You are an expert...")
        print(result.suggested_prompt)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None
    ):
        """
        Initialize the Prompt Optimizer.

        Args:
            project_id: GCP project ID. Defaults to VAPO_CONFIG setting.
            location: GCP region. Defaults to VAPO_CONFIG setting.
        """
        self.project_id = project_id or VAPO_CONFIG.get("project_id")
        self.location = location or VAPO_CONFIG.get("location", "us-central1")

        if not self.project_id:
            raise ValueError(
                "Project ID required. Set GOOGLE_CLOUD_PROJECT env var or pass project_id."
            )

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        self.client = vertexai.Client(project=self.project_id, location=self.location)

        logger.info(f"PromptOptimizer initialized for project: {self.project_id}")

    def optimize_prompt(
        self,
        prompt: str,
        target_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize a prompt using Zero-Shot optimization.

        Args:
            prompt: The prompt text to optimize
            target_model: Optional target model to optimize for

        Returns:
            Dictionary with:
                - suggested_prompt: The optimized prompt text
                - raw_response: The raw API response
                - guidelines: List of optimization guidelines applied
        """
        try:
            logger.info(f"Optimizing prompt ({len(prompt)} chars)...")

            # Call the Zero-Shot optimizer
            response = self.client.prompts.optimize(prompt=prompt)

            result = {
                "original_prompt": prompt,
                "raw_response": response.raw_text_response,
                "guidelines": [],
            }

            # Extract the suggested prompt
            if response.parsed_response:
                result["suggested_prompt"] = response.parsed_response.suggested_prompt
                if hasattr(response.parsed_response, "guidelines"):
                    result["guidelines"] = response.parsed_response.guidelines
            else:
                # Fallback to raw response
                result["suggested_prompt"] = response.raw_text_response

            logger.info("Prompt optimization completed")
            return result

        except Exception as e:
            logger.error(f"Prompt optimization failed: {e}")
            raise

    def optimize_system_instruction(
        self,
        system_prompt: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize a system instruction/prompt.

        Args:
            system_prompt: The system instruction to optimize
            context: Optional context about what the system does

        Returns:
            Optimization result dictionary
        """
        # Build the optimization request
        optimization_request = f"""Optimize this system instruction for an AI assistant:

{system_prompt}
"""
        if context:
            optimization_request += f"\nContext: {context}"

        return self.optimize_prompt(optimization_request)

    def optimize_user_template(
        self,
        template: str,
        variables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Optimize a user prompt template (with Jinja2 variables).

        Args:
            template: The Jinja2 template string
            variables: List of variable names used in the template

        Returns:
            Optimization result dictionary
        """
        # Build the optimization request, preserving template variables
        optimization_request = f"""Optimize this user prompt template.
IMPORTANT: Preserve all template variables in the format {{{{ variable_name }}}} or {{% if %}} blocks.

Template:
{template}
"""
        if variables:
            optimization_request += f"\nTemplate variables used: {', '.join(variables)}"

        return self.optimize_prompt(optimization_request)


class BatchPromptOptimizer:
    """
    Batch optimizer for multiple prompts from the prompts directory.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        prompts_dir: Optional[str] = None
    ):
        """
        Initialize the batch optimizer.

        Args:
            project_id: GCP project ID
            prompts_dir: Path to prompts directory
        """
        self.optimizer = PromptOptimizer(project_id=project_id)

        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = Path(prompts_dir)

        # Load registry
        registry_path = self.prompts_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path) as f:
                self.registry = json.load(f)
        else:
            self.registry = {}

    def optimize_all(
        self,
        prompt_ids: Optional[List[str]] = None,
        save_results: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Optimize all prompts (or a subset).

        Args:
            prompt_ids: Optional list of prompt IDs to optimize. If None, optimizes all.
            save_results: Whether to save optimized versions to files

        Returns:
            Dictionary mapping prompt_id to optimization results
        """
        if prompt_ids is None:
            prompt_ids = list(self.registry.keys())

        results = {}

        for prompt_id in prompt_ids:
            if prompt_id not in self.registry:
                logger.warning(f"Prompt '{prompt_id}' not found in registry, skipping")
                continue

            logger.info(f"Optimizing prompt: {prompt_id}")

            try:
                result = self.optimize_prompt(prompt_id)
                results[prompt_id] = result

                if save_results:
                    self._save_optimized_version(prompt_id, result)

            except Exception as e:
                logger.error(f"Failed to optimize '{prompt_id}': {e}")
                results[prompt_id] = {"error": str(e)}

        return results

    def optimize_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Optimize a single prompt by ID.

        Args:
            prompt_id: The prompt identifier

        Returns:
            Dictionary with original and optimized prompts
        """
        if prompt_id not in self.registry:
            raise ValueError(f"Prompt '{prompt_id}' not found in registry")

        # Load the prompt file
        prompt_file = self.prompts_dir / self.registry[prompt_id]["file"]
        with open(prompt_file) as f:
            prompt_data = json.load(f)

        # Get the production version
        versions = prompt_data.get("versions", [])
        production = next(
            (v for v in versions if v.get("status") == "production"),
            versions[0] if versions else None
        )

        if not production:
            raise ValueError(f"No production version found for '{prompt_id}'")

        result = {
            "prompt_id": prompt_id,
            "original_version": production["version"],
            "optimized_at": datetime.utcnow().isoformat() + "Z",
        }

        # Optimize system prompt if present
        system_prompt = production.get("system_prompt")
        if system_prompt:
            logger.info(f"  Optimizing system prompt...")
            sys_result = self.optimizer.optimize_system_instruction(
                system_prompt,
                context=self.registry[prompt_id].get("description")
            )
            result["system_prompt"] = {
                "original": system_prompt,
                "optimized": sys_result.get("suggested_prompt"),
                "guidelines": sys_result.get("guidelines", []),
            }

        # Optimize user template if present
        user_template = production.get("user_prompt_template")
        if user_template:
            logger.info(f"  Optimizing user template...")
            variables = self.registry[prompt_id].get("variables", [])
            template_result = self.optimizer.optimize_user_template(
                user_template,
                variables=variables
            )
            result["user_prompt_template"] = {
                "original": user_template,
                "optimized": template_result.get("suggested_prompt"),
                "guidelines": template_result.get("guidelines", []),
            }

        return result

    def _save_optimized_version(
        self,
        prompt_id: str,
        optimization_result: Dict[str, Any]
    ) -> str:
        """
        Save an optimized version to the prompt file.

        Args:
            prompt_id: The prompt identifier
            optimization_result: The optimization result from optimize_prompt()

        Returns:
            The new version number
        """
        prompt_file = self.prompts_dir / self.registry[prompt_id]["file"]
        with open(prompt_file) as f:
            prompt_data = json.load(f)

        # Generate new version number
        versions = prompt_data.get("versions", [])
        latest_version = versions[-1]["version"] if versions else "1.0.0"

        # Parse version and increment
        parts = latest_version.replace("-vapo", "").split(".")
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
        new_version = f"{major}.{minor + 1}.0-vapo"

        # Build new version entry
        new_entry = {
            "version": new_version,
            "status": "staging",
            "created_at": optimization_result.get("optimized_at", datetime.utcnow().isoformat() + "Z"),
            "optimization_source": "vapo_zero_shot",
        }

        # Add optimized system prompt
        if "system_prompt" in optimization_result:
            sys_data = optimization_result["system_prompt"]
            new_entry["system_prompt"] = sys_data.get("optimized") or sys_data.get("original")
            if sys_data.get("guidelines"):
                new_entry["system_prompt_guidelines"] = sys_data["guidelines"]

        # Add optimized user template
        if "user_prompt_template" in optimization_result:
            template_data = optimization_result["user_prompt_template"]
            new_entry["user_prompt_template"] = template_data.get("optimized") or template_data.get("original")
            if template_data.get("guidelines"):
                new_entry["user_template_guidelines"] = template_data["guidelines"]

        # Append new version
        prompt_data["versions"].append(new_entry)

        # Save back
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f, indent=2)

        logger.info(f"Saved optimized version {new_version} for '{prompt_id}'")
        return new_version

    def generate_report(
        self,
        results: Dict[str, Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a comparison report of original vs optimized prompts.

        Args:
            results: The results from optimize_all()
            output_path: Optional path to save the report

        Returns:
            The report as a string
        """
        lines = [
            "# Prompt Optimization Report",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            f"Project: {self.optimizer.project_id}",
            "",
            "---",
            "",
        ]

        for prompt_id, result in results.items():
            lines.append(f"## {prompt_id}")
            lines.append("")

            if "error" in result:
                lines.append(f"**Error:** {result['error']}")
                lines.append("")
                continue

            lines.append(f"- Original version: {result.get('original_version', 'N/A')}")
            lines.append(f"- Optimized at: {result.get('optimized_at', 'N/A')}")
            lines.append("")

            # System prompt changes
            if "system_prompt" in result:
                sys_data = result["system_prompt"]
                lines.append("### System Prompt")
                lines.append("")
                lines.append("**Original (truncated):**")
                lines.append("```")
                lines.append(sys_data["original"][:500] + "..." if len(sys_data["original"]) > 500 else sys_data["original"])
                lines.append("```")
                lines.append("")
                if sys_data.get("optimized"):
                    lines.append("**Optimized (truncated):**")
                    lines.append("```")
                    opt = sys_data["optimized"]
                    lines.append(opt[:500] + "..." if len(opt) > 500 else opt)
                    lines.append("```")
                lines.append("")

            # User template changes
            if "user_prompt_template" in result:
                template_data = result["user_prompt_template"]
                lines.append("### User Template")
                lines.append("")
                lines.append("**Original (truncated):**")
                lines.append("```")
                orig = template_data["original"]
                lines.append(orig[:500] + "..." if len(orig) > 500 else orig)
                lines.append("```")
                lines.append("")
                if template_data.get("optimized"):
                    lines.append("**Optimized (truncated):**")
                    lines.append("```")
                    opt = template_data["optimized"]
                    lines.append(opt[:500] + "..." if len(opt) > 500 else opt)
                    lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w") as f:
                f.write(report)
            logger.info(f"Report saved to: {output_path}")

        return report


# Convenience function for quick optimization
def optimize_prompt_quick(prompt: str, project_id: Optional[str] = None) -> str:
    """
    Quick helper to optimize a single prompt.

    Args:
        prompt: The prompt to optimize
        project_id: Optional GCP project ID

    Returns:
        The optimized prompt text
    """
    optimizer = PromptOptimizer(project_id=project_id)
    result = optimizer.optimize_prompt(prompt)
    return result.get("suggested_prompt", prompt)
