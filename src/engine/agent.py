"""BrowserAgent — the main observe-think-act loop."""

import asyncio
import logging
import time
import traceback
from typing import Optional

logger = logging.getLogger(__name__)

from .actions import ActionExecutor
from .observer import PageObserver
from .session import SessionManager
from ..llm.client import LLMClient
from ..llm.prompts import SystemPromptBuilder
from ..llm.parser import ActionParser
from ..stealth.config import StealthConfig
from ..utils.helpers import format_page_state


class BrowserAgent:
    """Autonomous browser agent with observe-think-act loop."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_steps: int = 30,
        headless: bool = True,
        screenshot_dir: Optional[str] = None,
        session_id: Optional[str] = None,
        human_delay: tuple[float, float] = (0.5, 2.0),
        user_data_dir: Optional[str] = None,
        verbose: bool = True,
    ):
        self.max_steps = max_steps
        self.headless = headless
        self.screenshot_dir = screenshot_dir
        self.session_id = session_id or f"session_{int(time.time())}"
        self.human_delay = human_delay
        self.user_data_dir = user_data_dir
        self.verbose = verbose

        self.llm = llm_client or LLMClient()
        self.stealth = StealthConfig()
        self.session_manager = SessionManager()
        self.browser = None
        self.context = None
        self.page = None
        self.observer = None
        self.executor = None
        self._stuck_counter = 0
        self._last_state_signature = ""

    async def run(self, goal: str) -> dict:
        """Execute a task from a goal string.

        Returns dict with: success, result, steps, error (optional).
        """
        if self.verbose:
            logger.info("─" * 60)
            logger.info("🤖 BrowserBot: %s", goal)
            logger.info("─" * 60)

        try:
            await self._setup_browser()
            steps_taken = 0
            result = None
            error = None

            for step in range(1, self.max_steps + 1):
                steps_taken = step
                if self.verbose:
                    logger.info("--- Step %d/%d ---", step, self.max_steps)

                # OBSERVE
                page_state = await self.observer.observe()
                page_state["goal"] = goal

                if self.verbose:
                    logger.info("📍 URL: %s", page_state['url'])
                    logger.info("📄 Title: %s", page_state['title'])
                    elements = page_state.get("interactive_elements", [])
                    logger.info("🔘 Elements: %d found", len(elements))

                # Check stuck detection
                state_sig = f"{page_state['url']}|{page_state['visible_text'][:200]}"
                if state_sig == self._last_state_signature:
                    self._stuck_counter += 1
                else:
                    self._stuck_counter = 0
                    self._last_state_signature = state_sig

                if self._stuck_counter >= 3:
                    if self.verbose:
                        logger.warning("⚠️  Stuck detected — trying navigation to original goal")
                    page_state["stuck"] = True

                # THINK — get LLM decision
                action = await self._think(goal, page_state)

                if action is None:
                    # Demo mode fallback or error
                    if self.llm.demo_mode:
                        action = self.llm.get_demo_action(page_state)
                    else:
                        error = "Failed to parse LLM response"
                        break

                if self.verbose:
                    logger.info("🧠 Action: %s", action['action'])
                    logger.info("💬 Reasoning: %s", action.get('reasoning', ''))
                    logger.info("⚙️  Params: %s", action.get('params', {}))

                # ACT
                exec_result = await self.executor.execute(
                    action["action"],
                    action.get("params", {}),
                    step=step,
                )

                if not exec_result["success"]:
                    if self.verbose:
                        logger.error("❌ Action failed: %s", exec_result['result'])

                # Human-like delay
                delay = self.stealth.random_delay(*self.human_delay)
                await asyncio.sleep(delay)

                # Check if done
                if action["action"] == "done":
                    result = exec_result.get("result", action.get("params", {}).get("result", "Task completed."))
                    if self.verbose:
                        logger.info("✅ Task complete: %s", result)
                    break

            # Save session
            await self.session_manager.save_state(self.context, self.session_id)

            return {
                "success": result is not None,
                "result": result or "Max steps reached without completion.",
                "steps": steps_taken,
                "error": error,
            }

        except Exception as e:
            logger.exception("Unhandled exception in agent loop")
            return {
                "success": False,
                "result": None,
                "steps": 0,
                "error": str(e),
            }
        finally:
            await self._cleanup()

    async def _setup_browser(self):
        """Initialize Playwright browser with stealth configuration."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        launch_options = {
            "headless": self.headless,
        }

        user_agent = self.stealth.random_user_agent()
        viewport = self.stealth.random_viewport()

        # Use persistent context if user_data_dir is set
        if self.user_data_dir:
            self.context = await self._playwright.chromium.launch_persistent_context(
                self.user_data_dir,
                **launch_options,
                user_agent=user_agent,
                viewport=viewport,
                locale="en-US",
                timezone_id="America/New_York",
            )
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        else:
            self.browser = await self._playwright.chromium.launch(**launch_options)
            self.context = await self.browser.new_context(
                user_agent=user_agent,
                viewport=viewport,
                locale="en-US",
                timezone_id="America/New_York",
            )
            self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(15000)

        # Restore session if available
        await self.session_manager.load_state(self.context, self.session_id)

        # Initialize observer and executor
        self.observer = PageObserver(self.page)
        self.executor = ActionExecutor(self.page, screenshot_dir=self.screenshot_dir)

    async def _think(self, goal: str, page_state: dict) -> Optional[dict]:
        """Send page state to LLM and parse the response."""
        system_prompt = SystemPromptBuilder.build(max_steps=self.max_steps)
        formatted_state = format_page_state(page_state)

        user_message = f"""Task: {goal}

{formatted_state}

Respond with the next action in JSON format."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        response = await self.llm.chat(messages)

        if response:
            if self.verbose:
                logger.info("🤖 LLM Response: %s...", response[:200])
            return ActionParser.parse(response)

        return None

    async def _cleanup(self):
        """Clean up browser resources."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "_playwright") and self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
