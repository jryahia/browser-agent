"""Example: Fill out a multi-step form."""

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
        max_steps=25,
        headless=True,
    )
    result = await agent.run(
        "Go to http://httpbin.org/forms/post, fill in the customer name as 'John Doe', "
        "and tell me the form fields you see"
    )

    if result["success"]:
        print(f"\n✅ Result: {result['result']}")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    print(f"Steps: {result['steps']}")


if __name__ == "__main__":
    asyncio.run(main())
