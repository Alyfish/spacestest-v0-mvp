#!/usr/bin/env python3
"""
VAPO (Vertex AI Prompt Optimizer) Optimization Script

This script runs prompt optimization using Google's Vertex AI Prompt Optimizer.
It supports both zero-shot optimization (no data required) and data-driven
optimization (requires evaluation datasets).

Usage:
    # Run zero-shot optimization on a specific prompt
    python scripts/run_vapo_optimization.py --prompt color_agent --mode zero_shot

    # Run zero-shot optimization on all priority prompts
    python scripts/run_vapo_optimization.py --all --mode zero_shot

    # Run data-driven optimization (requires dataset)
    python scripts/run_vapo_optimization.py --prompt color_agent --mode data_driven \
        --dataset gs://bucket/color_agent.jsonl

    # Dry run (show what would be optimized without making changes)
    python scripts/run_vapo_optimization.py --all --mode zero_shot --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from prompt_manager import PromptManager
from vapo import VAPOClient
from config import VAPO_CONFIG


def load_prompt_content(prompt_manager: PromptManager, prompt_id: str) -> dict:
    """Load the full prompt content for optimization."""
    prompt_data = prompt_manager._load_prompt(prompt_id)
    if not prompt_data:
        raise ValueError(f"Prompt '{prompt_id}' not found")

    # Get production version
    versions = prompt_data.get("versions", [])
    production = next(
        (v for v in versions if v.get("status") == "production"),
        versions[0] if versions else None
    )

    if not production:
        raise ValueError(f"No production version found for '{prompt_id}'")

    return {
        "prompt_id": prompt_id,
        "version": production["version"],
        "system_prompt": production.get("system_prompt"),
        "user_prompt_template": production.get("user_prompt_template", ""),
    }


def run_zero_shot_optimization(
    vapo_client: VAPOClient,
    prompt_manager: PromptManager,
    prompt_id: str,
    dry_run: bool = False,
    auto_save: bool = True,
) -> dict:
    """Run zero-shot optimization on a single prompt."""
    print(f"\n{'='*60}")
    print(f"Optimizing: {prompt_id}")
    print(f"{'='*60}")

    # Load the prompt
    content = load_prompt_content(prompt_manager, prompt_id)

    # Combine system and user prompts for optimization
    full_prompt = ""
    if content["system_prompt"]:
        full_prompt = f"[SYSTEM]\n{content['system_prompt']}\n\n[USER]\n"
    full_prompt += content["user_prompt_template"]

    print(f"  Current version: {content['version']}")
    print(f"  Prompt length: {len(full_prompt)} characters")

    if dry_run:
        print("  [DRY RUN] Would optimize this prompt")
        return {"prompt_id": prompt_id, "status": "dry_run"}

    # Run optimization
    result = vapo_client.optimize_zero_shot(full_prompt)

    if result["success"]:
        print(f"  ✓ Optimization successful!")
        print(f"  Guidelines applied: {len(result['applicable_guidelines'])}")

        for i, guideline in enumerate(result["applicable_guidelines"][:5], 1):
            print(f"    {i}. {guideline[:80]}...")

        # Calculate improvement
        original_len = len(full_prompt)
        optimized_len = len(result["suggested_prompt"])
        change_pct = ((optimized_len - original_len) / original_len) * 100
        print(f"  Length change: {change_pct:+.1f}%")

        # Save if auto_save enabled
        if auto_save and result["suggested_prompt"] != full_prompt:
            new_version = prompt_manager.add_optimized_version(
                prompt_id=prompt_id,
                optimized_prompt=result["suggested_prompt"],
                optimization_source="vapo_zero_shot",
                guidelines=result["applicable_guidelines"],
            )
            print(f"  → Saved as version: {new_version}")
            result["new_version"] = new_version
    else:
        print(f"  ✗ Optimization failed: {result.get('error', 'Unknown error')}")

    return result


def run_data_driven_optimization(
    vapo_client: VAPOClient,
    prompt_manager: PromptManager,
    prompt_id: str,
    dataset_uri: str,
    target_model: str = "gemini-2.5-flash",
    dry_run: bool = False,
) -> dict:
    """Run data-driven optimization on a single prompt."""
    print(f"\n{'='*60}")
    print(f"Data-Driven Optimization: {prompt_id}")
    print(f"{'='*60}")

    # Load the prompt
    content = load_prompt_content(prompt_manager, prompt_id)

    print(f"  Current version: {content['version']}")
    print(f"  Dataset: {dataset_uri}")
    print(f"  Target model: {target_model}")

    if dry_run:
        print("  [DRY RUN] Would run data-driven optimization")
        return {"prompt_id": prompt_id, "status": "dry_run"}

    # Run optimization
    result = vapo_client.optimize_data_driven(
        system_instruction=content["system_prompt"] or "",
        prompt_template=content["user_prompt_template"],
        dataset_uri=dataset_uri,
        target_model=target_model,
        wait_for_completion=True,
    )

    if result["success"]:
        print(f"  ✓ Optimization successful!")
        if "best_instruction" in result:
            print(f"  Best instruction preview: {result['best_instruction'][:100]}...")
        if "metrics_improvement" in result:
            print(f"  Metrics improvement: {result['metrics_improvement']}")
    else:
        print(f"  ✗ Optimization failed: {result.get('error', 'Unknown error')}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Run VAPO prompt optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="Prompt ID to optimize (e.g., color_agent)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Optimize all priority prompts",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["zero_shot", "data_driven"],
        default="zero_shot",
        help="Optimization mode (default: zero_shot)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="GCS URI for evaluation dataset (required for data_driven mode)",
    )
    parser.add_argument(
        "--target-model",
        type=str,
        default="gemini-2.5-flash",
        help="Target model for data-driven optimization",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be optimized without making changes",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save optimized prompts to registry",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="GCP project ID (overrides GOOGLE_CLOUD_PROJECT)",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="us-central1",
        help="GCP location for Vertex AI",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.prompt and not args.all:
        parser.error("Either --prompt or --all is required")

    if args.mode == "data_driven" and not args.dataset:
        parser.error("--dataset is required for data_driven mode")

    # Initialize clients
    prompts_dir = backend_dir / "prompts"
    prompt_manager = PromptManager(prompts_dir=prompts_dir)

    project_id = args.project_id or VAPO_CONFIG.get("project_id")
    vapo_client = VAPOClient(project_id=project_id, location=args.location)

    # Determine which prompts to optimize
    if args.all:
        prompt_ids = VAPO_CONFIG.get("priority_prompts", [])
        print(f"Optimizing {len(prompt_ids)} priority prompts...")
    else:
        prompt_ids = [args.prompt]

    # Run optimization
    results = {}
    for prompt_id in prompt_ids:
        try:
            if args.mode == "zero_shot":
                result = run_zero_shot_optimization(
                    vapo_client=vapo_client,
                    prompt_manager=prompt_manager,
                    prompt_id=prompt_id,
                    dry_run=args.dry_run,
                    auto_save=not args.no_save,
                )
            else:
                result = run_data_driven_optimization(
                    vapo_client=vapo_client,
                    prompt_manager=prompt_manager,
                    prompt_id=prompt_id,
                    dataset_uri=args.dataset,
                    target_model=args.target_model,
                    dry_run=args.dry_run,
                )
            results[prompt_id] = result
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[prompt_id] = {"error": str(e), "success": False}

    # Summary
    print(f"\n{'='*60}")
    print("OPTIMIZATION SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for r in results.values() if r.get("success"))
    failed = sum(1 for r in results.values() if not r.get("success") and r.get("status") != "dry_run")
    dry_run_count = sum(1 for r in results.values() if r.get("status") == "dry_run")

    print(f"  Total: {len(results)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    if dry_run_count:
        print(f"  Dry run: {dry_run_count}")

    # Save results if output specified
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": args.mode,
            "results": results,
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
