#!/usr/bin/env python3
"""BrowserBot CLI — Run autonomous browser tasks from the command line."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from src.engine.agent import BrowserAgent
from src.llm.client import LLMClient

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="BrowserBot — Autonomous Browser Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Go to example.com and tell me the page title"
  python main.py --tasks tasks.json --headless
  python main.py "Search Google for Python" --screenshots --output ./sessions/ --visible
        """,
    )
    parser.add_argument("goal", nargs="?", help="Task goal (e.g., 'Find the price of RTX 4090')")
    parser.add_argument("--tasks", help="JSON file with batch tasks")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless (default: True)")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    parser.add_argument("--max-steps", type=int, default=30, help="Maximum steps (default: 30)")
    parser.add_argument("--screenshots", action="store_true", help="Save screenshots at each step")
    parser.add_argument("--output", default="./sessions", help="Output directory")
    parser.add_argument("--session-id", help="Session ID for persistence")
    parser.add_argument("--provider", default="openai",
                        choices=["openai", "deepseek", "openrouter", "anthropic"],
                        help="LLM provider")
    parser.add_argument("--model", help="LLM model name")

    args = parser.parse_args()

    # Handle visible mode
    headless = not args.visible if args.visible else args.headless

    # Prepare screenshot directory
    screenshot_dir = None
    if args.screenshots:
        screenshot_dir = str(Path(args.output) / "screenshots")
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    # Batch mode from file
    if args.tasks:
        import json
        try:
            with open(args.tasks) as f:
                tasks = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error("Error loading tasks file: %s", e)
            sys.exit(1)

        if isinstance(tasks, list):
            for task_item in tasks:
                goal = task_item.get("goal", task_item if isinstance(task_item, str) else "")
                if goal:
                    asyncio.run(run_single_task(goal, args, headless, screenshot_dir))
        elif isinstance(tasks, dict) and "tasks" in tasks:
            for task_item in tasks["tasks"]:
                goal = task_item.get("goal", "")
                if goal:
                    asyncio.run(run_single_task(goal, args, headless, screenshot_dir))
        return

    # Single task mode
    if not args.goal:
        parser.print_help()
        sys.exit(1)

    asyncio.run(run_single_task(args.goal, args, headless, screenshot_dir))


async def run_single_task(goal: str, args, headless: bool, screenshot_dir: str):
    """Run a single task."""
    llm = LLMClient(provider=args.provider, model=args.model)
    agent = BrowserAgent(
        llm_client=llm,
        max_steps=args.max_steps,
        headless=headless,
        screenshot_dir=screenshot_dir,
        session_id=args.session_id,
    )
    result = await agent.run(goal)

    logger.info("─" * 60)
    if result["success"]:
        logger.info("✅ Success: %s", result['result'])
    else:
        logger.info("❌ Failed: %s", result.get('error', 'Unknown error'))
    logger.info("📊 Steps: %s", result['steps'])
    logger.info("─" * 60)

    return result


if __name__ == "__main__":
    main()
