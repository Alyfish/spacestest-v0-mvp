"""
Prompt Manager for VAPO (Vertex AI Prompt Optimizer) Integration

This module provides:
- Loading prompts from the JSON registry with versioning
- Jinja2-style variable interpolation
- A/B test allocation between production and optimized prompts
- Logging for which version was used
"""

import json
import os
import random
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt loading, versioning, and A/B testing for VAPO integration.

    Usage:
        pm = PromptManager()
        prompt, version = pm.get_prompt("color_agent", {
            "space_type": "bedroom",
            "palette_name": "Warm Earth",
            "palette_colors": ["#E8DCC8", "#A08060"]
        })
    """

    def __init__(
        self,
        prompts_dir: Optional[str] = None,
        ab_test_allocation: float = 0.0,
        enable_logging: bool = True
    ):
        """
        Initialize the PromptManager.

        Args:
            prompts_dir: Path to the prompts directory. Defaults to ./prompts
            ab_test_allocation: Fraction of traffic to route to optimized prompts (0.0-1.0)
            enable_logging: Whether to log prompt version usage
        """
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = Path(prompts_dir)
        self.ab_test_allocation = ab_test_allocation
        self.enable_logging = enable_logging

        # Initialize Jinja2 environment
        self.jinja_env = Environment(loader=BaseLoader())

        # Load the registry
        self._registry: Dict[str, Any] = {}
        self._prompts_cache: Dict[str, Any] = {}
        self._load_registry()

        # Usage log for tracking
        self._usage_log: List[Dict[str, Any]] = []

    def _load_registry(self) -> None:
        """Load the prompt registry from registry.json."""
        registry_path = self.prompts_dir / "registry.json"
        if registry_path.exists():
            with open(registry_path, "r") as f:
                self._registry = json.load(f)
            logger.info(f"Loaded prompt registry with {len(self._registry)} prompts")
        else:
            logger.warning(f"Prompt registry not found at {registry_path}")
            self._registry = {}

    def _load_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Load a specific prompt file."""
        if prompt_id in self._prompts_cache:
            return self._prompts_cache[prompt_id]

        if prompt_id not in self._registry:
            logger.error(f"Prompt '{prompt_id}' not found in registry")
            return None

        prompt_file = self.prompts_dir / self._registry[prompt_id]["file"]
        if not prompt_file.exists():
            logger.error(f"Prompt file not found: {prompt_file}")
            return None

        with open(prompt_file, "r") as f:
            prompt_data = json.load(f)

        self._prompts_cache[prompt_id] = prompt_data
        return prompt_data

    def _select_version(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select a prompt version based on A/B test allocation.

        Returns the production version unless:
        1. A/B testing is enabled (ab_test_allocation > 0)
        2. Random selection falls within the test allocation
        3. A staging/test version exists
        """
        versions = prompt_data.get("versions", [])
        if not versions:
            raise ValueError("No versions found in prompt data")

        # Find production and test versions
        production = None
        test_versions = []

        for v in versions:
            if v.get("status") == "production":
                production = v
            elif v.get("status") in ("staging", "a/b_test", "optimized"):
                test_versions.append(v)

        if not production:
            # Fallback to first version if no production version
            production = versions[0]

        # A/B test selection
        if test_versions and self.ab_test_allocation > 0:
            if random.random() < self.ab_test_allocation:
                # Select a test version (first one for simplicity)
                return test_versions[0]

        return production

    def _interpolate(self, template: str, context: Dict[str, Any]) -> str:
        """
        Interpolate variables into a prompt template using Jinja2.

        Args:
            template: The Jinja2 template string
            context: Dictionary of variables to interpolate

        Returns:
            The interpolated prompt string
        """
        try:
            jinja_template = self.jinja_env.from_string(template)
            return jinja_template.render(**context)
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            # Fallback: simple string replacement for f-string style
            result = template
            for key, value in context.items():
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                result = result.replace(f"{{{{ {key} }}}}", str(value))
                result = result.replace(f"{{{key}}}", str(value))
            return result

    def _log_usage(
        self,
        prompt_id: str,
        version: str,
        context_keys: List[str]
    ) -> None:
        """Log prompt version usage for metrics tracking."""
        if not self.enable_logging:
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_id": prompt_id,
            "version": version,
            "context_keys": context_keys,
        }
        self._usage_log.append(log_entry)

        # Keep log size manageable
        if len(self._usage_log) > 10000:
            self._usage_log = self._usage_log[-5000:]

        logger.debug(f"Prompt usage: {prompt_id} v{version}")

    def get_prompt(
        self,
        prompt_id: str,
        context: Dict[str, Any],
        force_version: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Get an interpolated prompt with version tracking.

        Args:
            prompt_id: The prompt identifier (e.g., "color_agent")
            context: Dictionary of variables to interpolate
            force_version: Optional specific version to use (bypasses A/B test)

        Returns:
            Tuple of (interpolated_prompt, version_id)
        """
        prompt_data = self._load_prompt(prompt_id)
        if not prompt_data:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # Select version
        if force_version:
            version = next(
                (v for v in prompt_data["versions"] if v["version"] == force_version),
                None
            )
            if not version:
                raise ValueError(f"Version '{force_version}' not found for prompt '{prompt_id}'")
        else:
            version = self._select_version(prompt_data)

        # Get the template
        template = version.get("user_prompt_template", "")

        # Interpolate
        prompt = self._interpolate(template, context)

        # Log usage
        self._log_usage(prompt_id, version["version"], list(context.keys()))

        return prompt, version["version"]

    def get_system_prompt(
        self,
        prompt_id: str,
        context: Optional[Dict[str, Any]] = None,
        force_version: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Get the system prompt for a given prompt ID.

        Args:
            prompt_id: The prompt identifier
            context: Optional variables to interpolate
            force_version: Optional specific version to use

        Returns:
            Tuple of (system_prompt, version_id) or (None, version_id) if no system prompt
        """
        prompt_data = self._load_prompt(prompt_id)
        if not prompt_data:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # Select version
        if force_version:
            version = next(
                (v for v in prompt_data["versions"] if v["version"] == force_version),
                None
            )
            if not version:
                raise ValueError(f"Version '{force_version}' not found")
        else:
            version = self._select_version(prompt_data)

        system_prompt = version.get("system_prompt")

        # Interpolate if context provided
        if system_prompt and context:
            system_prompt = self._interpolate(system_prompt, context)

        return system_prompt, version["version"]

    def get_full_prompt(
        self,
        prompt_id: str,
        context: Dict[str, Any],
        force_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get both system and user prompts with full metadata.

        Args:
            prompt_id: The prompt identifier
            context: Dictionary of variables to interpolate
            force_version: Optional specific version to use

        Returns:
            Dictionary with system_prompt, user_prompt, version, and metadata
        """
        prompt_data = self._load_prompt(prompt_id)
        if not prompt_data:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # Select version
        if force_version:
            version = next(
                (v for v in prompt_data["versions"] if v["version"] == force_version),
                None
            )
            if not version:
                raise ValueError(f"Version '{force_version}' not found")
        else:
            version = self._select_version(prompt_data)

        # Get and interpolate prompts
        system_prompt = version.get("system_prompt")
        user_prompt = version.get("user_prompt_template", "")

        if system_prompt:
            system_prompt = self._interpolate(system_prompt, context)
        user_prompt = self._interpolate(user_prompt, context)

        # Log usage
        self._log_usage(prompt_id, version["version"], list(context.keys()))

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "version": version["version"],
            "status": version.get("status", "unknown"),
            "prompt_id": prompt_id,
        }

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts with their metadata."""
        prompts = []
        for prompt_id, metadata in self._registry.items():
            prompts.append({
                "prompt_id": prompt_id,
                "category": metadata.get("category"),
                "description": metadata.get("description"),
                "variables": metadata.get("variables", []),
            })
        return prompts

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for A/B testing analysis."""
        if not self._usage_log:
            return {"total_requests": 0, "by_prompt": {}, "by_version": {}}

        by_prompt: Dict[str, int] = {}
        by_version: Dict[str, Dict[str, int]] = {}

        for entry in self._usage_log:
            prompt_id = entry["prompt_id"]
            version = entry["version"]

            by_prompt[prompt_id] = by_prompt.get(prompt_id, 0) + 1

            if prompt_id not in by_version:
                by_version[prompt_id] = {}
            by_version[prompt_id][version] = by_version[prompt_id].get(version, 0) + 1

        return {
            "total_requests": len(self._usage_log),
            "by_prompt": by_prompt,
            "by_version": by_version,
        }

    def add_optimized_version(
        self,
        prompt_id: str,
        optimized_prompt: str,
        optimization_source: str = "vapo_zero_shot",
        guidelines: Optional[List[str]] = None
    ) -> str:
        """
        Add an optimized version of a prompt from VAPO.

        Args:
            prompt_id: The prompt identifier
            optimized_prompt: The optimized prompt text
            optimization_source: Source of optimization (vapo_zero_shot, vapo_data_driven)
            guidelines: Optional list of guidelines applied

        Returns:
            The new version number
        """
        prompt_data = self._load_prompt(prompt_id)
        if not prompt_data:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # Generate new version number
        versions = prompt_data.get("versions", [])
        latest_version = versions[-1]["version"] if versions else "1.0.0"
        major, minor, patch = map(int, latest_version.split("."))
        new_version = f"{major}.{minor + 1}.0-vapo"

        # Create new version entry
        new_entry = {
            "version": new_version,
            "status": "staging",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "user_prompt_template": optimized_prompt,
            "optimization_source": optimization_source,
        }

        if guidelines:
            new_entry["applied_guidelines"] = guidelines

        # Copy system prompt from production if it exists
        for v in versions:
            if v.get("status") == "production" and v.get("system_prompt"):
                new_entry["system_prompt"] = v["system_prompt"]
                break

        # Add to versions
        prompt_data["versions"].append(new_entry)

        # Save back to file
        prompt_file = self.prompts_dir / self._registry[prompt_id]["file"]
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f, indent=2)

        # Clear cache
        if prompt_id in self._prompts_cache:
            del self._prompts_cache[prompt_id]

        logger.info(f"Added optimized version {new_version} for prompt '{prompt_id}'")
        return new_version

    def promote_version(self, prompt_id: str, version: str) -> None:
        """
        Promote a version to production status.

        Args:
            prompt_id: The prompt identifier
            version: The version to promote
        """
        prompt_data = self._load_prompt(prompt_id)
        if not prompt_data:
            raise ValueError(f"Prompt '{prompt_id}' not found")

        # Demote current production
        for v in prompt_data["versions"]:
            if v.get("status") == "production":
                v["status"] = "archived"

        # Promote new version
        for v in prompt_data["versions"]:
            if v["version"] == version:
                v["status"] = "production"
                v["promoted_at"] = datetime.utcnow().isoformat() + "Z"
                break
        else:
            raise ValueError(f"Version '{version}' not found")

        # Save back to file
        prompt_file = self.prompts_dir / self._registry[prompt_id]["file"]
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f, indent=2)

        # Clear cache
        if prompt_id in self._prompts_cache:
            del self._prompts_cache[prompt_id]

        logger.info(f"Promoted version {version} to production for prompt '{prompt_id}'")


# Global instance for convenience
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(
    ab_test_allocation: Optional[float] = None
) -> PromptManager:
    """
    Get or create the global PromptManager instance.

    Args:
        ab_test_allocation: Optional A/B test allocation to set

    Returns:
        The PromptManager instance
    """
    global _prompt_manager

    if _prompt_manager is None:
        allocation = ab_test_allocation if ab_test_allocation is not None else 0.0
        _prompt_manager = PromptManager(ab_test_allocation=allocation)

    return _prompt_manager
