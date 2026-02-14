"""
Vertex AI Prompt Optimizer (VAPO) Client

This client wraps the Vertex AI Prompt Optimizer API for both zero-shot
and data-driven prompt optimization.

Zero-shot optimization:
- Automatically refines prompts using AI-powered guidelines
- No evaluation data required
- Returns suggested_prompt and applicable_guidelines

Data-driven optimization:
- Uses evaluation datasets (50-100 JSONL samples) to optimize prompts
- Requires metrics definition and target model selection
- Returns best_instruction and best_demonstrations
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class VAPOClient:
    """
    Client for Vertex AI Prompt Optimizer.

    Supports both zero-shot (no data) and data-driven (with evaluation dataset) optimization.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
    ):
        """
        Initialize the VAPO client.

        Args:
            project_id: GCP project ID. Defaults to GOOGLE_CLOUD_PROJECT env var.
            location: GCP location for Vertex AI. Defaults to us-central1.
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self._client = None
        self._initialized = False

        if not self.project_id:
            logger.warning(
                "GOOGLE_CLOUD_PROJECT not set. VAPO client will not be initialized. "
                "Set the environment variable or pass project_id to enable optimization."
            )

    def _ensure_initialized(self) -> bool:
        """
        Lazily initialize the Vertex AI client.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._initialized:
            return self._client is not None

        if not self.project_id:
            self._initialized = True
            return False

        try:
            import vertexai
            from vertexai.preview import prompt_optimizer

            vertexai.init(project=self.project_id, location=self.location)
            self._client = prompt_optimizer.PromptOptimizer()
            self._initialized = True
            logger.info(f"VAPO client initialized for project {self.project_id}")
            return True
        except ImportError:
            logger.error(
                "google-cloud-aiplatform not installed. "
                "Run: pip install google-cloud-aiplatform>=1.38.0"
            )
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize VAPO client: {e}")
            self._initialized = True
            return False

    def optimize_zero_shot(self, prompt: str) -> Dict[str, Any]:
        """
        Apply zero-shot optimization to a prompt.

        Zero-shot optimization uses AI-powered guidelines to improve prompts
        without requiring any evaluation data.

        Args:
            prompt: The prompt text to optimize

        Returns:
            Dictionary with:
                - suggested_prompt: The optimized prompt
                - applicable_guidelines: List of guidelines that were applied
                - original_prompt: The original prompt for reference
                - success: Whether optimization succeeded
        """
        if not self._ensure_initialized():
            logger.warning("VAPO client not initialized, returning original prompt")
            return {
                "suggested_prompt": prompt,
                "applicable_guidelines": [],
                "original_prompt": prompt,
                "success": False,
                "error": "VAPO client not initialized",
            }

        try:
            result = self._client.optimize_prompt(prompt=prompt)

            return {
                "suggested_prompt": result.suggested_prompt,
                "applicable_guidelines": list(result.applicable_guidelines or []),
                "original_prompt": prompt,
                "success": True,
                "optimized_at": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Zero-shot optimization failed: {e}")
            return {
                "suggested_prompt": prompt,
                "applicable_guidelines": [],
                "original_prompt": prompt,
                "success": False,
                "error": str(e),
            }

    def optimize_data_driven(
        self,
        system_instruction: str,
        prompt_template: str,
        dataset_uri: str,
        target_model: str = "gemini-2.5-flash",
        eval_metrics: Optional[List[Dict[str, Any]]] = None,
        qps: int = 1,
        wait_for_completion: bool = True,
    ) -> Dict[str, Any]:
        """
        Run data-driven VAPO optimization with an evaluation dataset.

        This method requires a JSONL dataset with 50-100 samples in the format:
        {"input": {...}, "output": {...}, "reference": "...", "score": 0.85}

        Args:
            system_instruction: The system prompt to optimize
            prompt_template: The user prompt template (Jinja2 style)
            dataset_uri: GCS URI to the evaluation dataset (gs://bucket/dataset.jsonl)
            target_model: Target model for optimization (default: gemini-2.5-flash)
            eval_metrics: List of metrics with name and weight
            qps: Queries per second limit (default: 1)
            wait_for_completion: Whether to wait for the job to complete

        Returns:
            Dictionary with optimization results
        """
        if not self._ensure_initialized():
            return {
                "success": False,
                "error": "VAPO client not initialized",
            }

        try:
            from vertexai.preview import prompt_optimizer

            # Default metrics if not provided
            if eval_metrics is None:
                eval_metrics = [{"name": "quality", "weight": 1.0}]

            # Build metrics list
            metrics = [
                prompt_optimizer.Metric(name=m["name"], weight=m.get("weight", 1.0))
                for m in eval_metrics
            ]

            # Create optimization config
            config = prompt_optimizer.PromptOptimizationConfig(
                system_instruction=system_instruction,
                prompt_template=prompt_template,
                target_model=target_model,
                evaluation_dataset_uri=dataset_uri,
                metrics=metrics,
                qps=qps,
            )

            # Run optimization
            if wait_for_completion:
                job = self._client.optimize_prompt_async(config=config)
                result = job.result()

                return {
                    "best_instruction": result.best_instruction,
                    "best_demonstrations": list(result.best_demonstrations or []),
                    "metrics_improvement": result.metrics_improvement,
                    "success": True,
                    "optimized_at": datetime.utcnow().isoformat() + "Z",
                }
            else:
                job = self._client.optimize_prompt_async(config=config)
                return {
                    "job_id": job.name,
                    "status": "running",
                    "success": True,
                }

        except Exception as e:
            logger.error(f"Data-driven optimization failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_optimization_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of an async optimization job.

        Args:
            job_id: The job ID returned from optimize_data_driven

        Returns:
            Dictionary with job status and results if complete
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "VAPO client not initialized"}

        try:
            from google.cloud import aiplatform

            job = aiplatform.CustomJob.get(job_id)

            if job.state.name == "JOB_STATE_SUCCEEDED":
                return {
                    "status": "completed",
                    "success": True,
                    # Results would need to be parsed from job output
                }
            elif job.state.name in ("JOB_STATE_FAILED", "JOB_STATE_CANCELLED"):
                return {
                    "status": job.state.name.lower(),
                    "success": False,
                    "error": job.error if hasattr(job, "error") else "Job failed",
                }
            else:
                return {
                    "status": job.state.name.lower(),
                    "success": True,
                }

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {"success": False, "error": str(e)}

    def batch_optimize_zero_shot(
        self,
        prompts: Dict[str, str],
        output_dir: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Optimize multiple prompts using zero-shot optimization.

        Args:
            prompts: Dictionary mapping prompt_id to prompt text
            output_dir: Optional directory to save results

        Returns:
            Dictionary mapping prompt_id to optimization results
        """
        results = {}

        for prompt_id, prompt_text in prompts.items():
            logger.info(f"Optimizing prompt: {prompt_id}")
            result = self.optimize_zero_shot(prompt_text)
            results[prompt_id] = result

            if result["success"]:
                logger.info(
                    f"  ✓ Optimized with {len(result['applicable_guidelines'])} guidelines"
                )
            else:
                logger.warning(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

        # Save results if output_dir provided
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_file = output_path / f"vapo_results_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(f"Results saved to {output_file}")

        return results

    def compare_prompts(
        self,
        original: str,
        optimized: str,
        test_inputs: List[Dict[str, Any]],
        model: str = "gemini-2.5-flash"
    ) -> Dict[str, Any]:
        """
        Compare original and optimized prompts on test inputs.

        Args:
            original: The original prompt template
            optimized: The optimized prompt template
            test_inputs: List of test input contexts
            model: Model to use for comparison

        Returns:
            Comparison results with metrics
        """
        # This would require running both prompts through Gemini and comparing outputs
        # For now, return a placeholder structure
        return {
            "original_prompt": original[:100] + "...",
            "optimized_prompt": optimized[:100] + "...",
            "test_count": len(test_inputs),
            "comparison": "Not yet implemented - requires Gemini API integration",
        }
