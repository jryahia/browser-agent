"""Example: Scrape product info from a page."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine.agent import BrowserAgent
from src.llm.client import LLMClient


async def main():
    llm = LLMClient()
    agent = BrowserAgent(
        llm_client=llm,
        max_steps=15,
        headless=True,
    )
    result = await agent.run("Go to books.toscrape.com and tell me the title of the first book")

    if result["success"]:
        print(f"\n✅ Result: {result['result']}")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    print(f"Steps: {result['steps']}")


if __name__ == "__main__":
    asyncio.run(main())
