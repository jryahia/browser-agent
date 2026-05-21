"""Example: Search Google and extract results."""

import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.agent import BrowserAgent
from src.llm.client import LLMClient


async def main():
    llm = LLMClient()
    agent = BrowserAgent(
        llm_client=llm,
        max_steps=20,
        headless=True,
        screenshot_dir="./sessions/google_search",
    )
    result = await agent.run("Go to google.com, search for 'Python programming', and tell me the first result title")

    if result["success"]:
        print(f"\n✅ Result: {result['result']}")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    print(f"Steps: {result['steps']}")


if __name__ == "__main__":
    asyncio.run(main())
