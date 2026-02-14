#!/usr/bin/env python3
"""
Prompt Optimization Script

Run Zero-Shot optimization on all prompts using Vertex AI Prompt Optimizer.

Usage:
    python scripts/optimize_prompts.py                    # Optimize all prompts
    python scripts/optimize_prompts.py --prompts color_agent style_agent
    python scripts/optimize_prompts.py --dry-run          # Preview without saving
    python scripts/optimize_prompts.py --report-only      # Generate report from existing optimizations
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompt_optimizer import BatchPromptOptimizer
from config import VAPO_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Optimize prompts using Vertex AI Prompt Optimizer"
    )
    parser.add_argument(
        "--prompts",
        nargs="+",
        help="Specific prompt IDs to optimize (default: all)"
    )
    parser.add_argument(
        "--project",
        help="GCP project ID (default: from VAPO_CONFIG)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview optimization without saving to files"
    )
    parser.add_argument(
        "--report",
        default="optimization_report.md",
        help="Output path for the comparison report"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating a report"
    )

    args = parser.parse_args()

    # Get project ID
    project_id = args.project or VAPO_CONFIG.get("project_id")
    if not project_id:
        logger.error("No project ID specified. Set GOOGLE_CLOUD_PROJECT env var or use --project")
        sys.exit(1)

    logger.info(f"Using GCP project: {project_id}")

    # Initialize optimizer
    try:
        optimizer = BatchPromptOptimizer(project_id=project_id)
    except Exception as e:
        logger.error(f"Failed to initialize optimizer: {e}")
        sys.exit(1)

    # Get prompt IDs to optimize
    prompt_ids = args.prompts
    if prompt_ids is None:
        # Use priority order from config, or all prompts
        prompt_ids = VAPO_CONFIG.get("priority_prompts") or list(optimizer.registry.keys())

    logger.info(f"Prompts to optimize: {', '.join(prompt_ids)}")

    # Run optimization
    save_results = not args.dry_run
    if args.dry_run:
        logger.info("DRY RUN - results will not be saved")

    results = optimizer.optimize_all(
        prompt_ids=prompt_ids,
        save_results=save_results
    )

    # Print summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION SUMMARY")
    print("=" * 60)

    success_count = 0
    error_count = 0

    for prompt_id, result in results.items():
        if "error" in result:
            print(f"  {prompt_id}: FAILED - {result['error']}")
            error_count += 1
        else:
            status = "optimized" if save_results else "previewed"
            print(f"  {prompt_id}: {status}")
            success_count += 1

    print("-" * 60)
    print(f"Total: {success_count} succeeded, {error_count} failed")
    print("=" * 60 + "\n")

    # Generate report
    if not args.no_report:
        report_path = Path(__file__).parent.parent / args.report
        report = optimizer.generate_report(results, output_path=str(report_path))
        print(f"Report saved to: {report_path}")

    # Exit with error code if any failures
    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
