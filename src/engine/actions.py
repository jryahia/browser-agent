"""Action executor — perform browser actions via Playwright."""

import asyncio
import base64
from pathlib import Path
from typing import Optional


class ActionExecutor:
    """Executes browser actions on a Playwright page."""

    def __init__(self, page, screenshot_dir: Optional[str] = None):
        self.page = page
        self.screenshot_dir = screenshot_dir
        if screenshot_dir:
            Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

    async def execute(self, action: str, params: dict, step: int = 0) -> dict:
        """Execute an action and return the result.

        Returns dict with keys: success, result, screenshot (optional).
        """
        handler = getattr(self, f"_{action}", None)
        if not handler:
            return {"success": False, "result": f"Unknown action: {action}"}

        try:
            result = await handler(params)
            screenshot = None
            if self.screenshot_dir:
                screenshot = await self._save_screenshot(step)
            return {"success": True, "result": result, "screenshot": screenshot}
        except Exception as e:
            return {"success": False, "result": f"Error executing {action}: {str(e)}"}

    async def _navigate(self, params: dict) -> str:
        """Navigate to a URL."""
        url = params.get("url", "")
        if not url.startswith("http"):
            url = "https://" + url
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"Navigated to {url}"

    async def _click(self, params: dict) -> str:
        """Click an element."""
        selector = params.get("selector", "")
        if not selector:
            return "No selector provided for click"
        await self.page.click(selector, timeout=10000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        return f"Clicked element: {selector}"

    async def _type(self, params: dict) -> str:
        """Type text into an input field."""
        selector = params.get("selector", "")
        text = params.get("text", "")
        if not selector:
            return "No selector provided for type"
        await self.page.click(selector, timeout=5000)
        await self.page.fill(selector, "")
        await asyncio.sleep(0.3)
        await self.page.type(selector, text, delay=50)
        return f"Typed '{text[:50]}...' into {selector}"

    async def _select(self, params: dict) -> str:
        """Select a dropdown option."""
        selector = params.get("selector", "")
        option = params.get("option", "")
        if not selector:
            return "No selector provided for select"
        await self.page.select_option(selector, option, timeout=5000)
        return f"Selected '{option}' in {selector}"

    async def _scroll(self, params: dict) -> str:
        """Scroll the page."""
        direction = params.get("direction", "down")
        amount = params.get("amount", 500)
        delta_y = amount if direction == "down" else -amount
        await self.page.evaluate(f"window.scrollBy(0, {delta_y})")
        await asyncio.sleep(0.5)
        return f"Scrolled {direction} by {amount}px"

    async def _extract(self, params: dict) -> str:
        """Extract text from elements."""
        selector = params.get("selector", "")
        if not selector:
            # Extract all visible text
            text = await self.page.inner_text("body")
            return (text or "").strip()[:2000]
        try:
            elements = await self.page.query_selector_all(selector)
            texts = []
            for el in elements[:20]:
                t = await el.inner_text()
                if t:
                    texts.append(t.strip())
            return "\n".join(texts)[:2000] if texts else "No elements found"
        except Exception as e:
            return f"Error extracting: {e}"

    async def _wait(self, params: dict) -> str:
        """Wait for a specified duration."""
        seconds = params.get("seconds", 2)
        await asyncio.sleep(seconds)
        return f"Waited {seconds}s"

    async def _screenshot(self, params: dict = None) -> str:
        """Take a screenshot and return as base64."""
        try:
            bytes_data = await self.page.screenshot(type="png", full_page=False)
            b64 = base64.b64encode(bytes_data).decode("utf-8")
            return b64
        except Exception as e:
            return f"Error taking screenshot: {e}"

    async def _done(self, params: dict) -> str:
        """Mark task as complete with result."""
        result = params.get("result", "Task completed.")
        return result

    async def _save_screenshot(self, step: int) -> str:
        """Save screenshot to file and return path."""
        try:
            path = Path(self.screenshot_dir) / f"step_{step:03d}.png"
            await self.page.screenshot(path=str(path))
            return str(path)
        except Exception:
            return ""
