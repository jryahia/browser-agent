"""Unified LLM client supporting OpenAI, DeepSeek, OpenRouter, and Anthropic."""

import os
import json
from typing import Optional


class LLMClient:
    """Unified LLM client that supports multiple providers."""

    SUPPORTED_PROVIDERS = {
        "openai": {"env_key": "OPENAI_API_KEY", "base_url": "https://api.openai.com/v1"},
        "deepseek": {"env_key": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1"},
        "openrouter": {"env_key": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1"},
        "anthropic": {"env_key": "ANTHROPIC_API_KEY", "base_url": None},
    }

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ):
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens

        if self.provider == "anthropic":
            self._init_anthropic(api_key, model)
        else:
            self._init_openai_compat(api_key, base_url, model)

        self.demo_mode = not self._check_key()

    def _init_openai_compat(self, api_key: Optional[str], base_url: Optional[str], model: Optional[str]):
        """Initialize OpenAI-compatible client."""
        provider_info = self.SUPPORTED_PROVIDERS.get(self.provider, self.SUPPORTED_PROVIDERS["openai"])
        self.api_key = api_key or os.environ.get(provider_info["env_key"]) or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or provider_info["base_url"]

        # Default models per provider
        self.model = model or {
            "openai": "gpt-4o-mini",
            "deepseek": "deepseek-chat",
            "openrouter": "openrouter/auto",
        }.get(self.provider, "gpt-4o-mini")

    def _init_anthropic(self, api_key: Optional[str], model: Optional[str]):
        """Initialize Anthropic client."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or "claude-3-haiku-20240307"

    def _check_key(self) -> bool:
        return bool(self.api_key)

    async def chat(self, messages: list[dict]) -> Optional[str]:
        """Send a chat completion request and return the response text."""
        if self.demo_mode:
            return None

        if self.provider == "anthropic":
            return await self._chat_anthropic(messages)
        return await self._chat_openai_compat(messages)

    async def _chat_openai_compat(self, messages: list[dict]) -> Optional[str]:
        """OpenAI-compatible API call."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible LLM call failed: {e}")

    async def _chat_anthropic(self, messages: list[dict]) -> Optional[str]:
        """Anthropic API call."""
        try:
            import anthropic

            # Convert OpenAI-style messages to Anthropic format
            system_msg = None
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": anthropic_messages,
                "temperature": self.temperature,
            }
            if system_msg:
                kwargs["system"] = system_msg

            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic LLM call failed: {e}")

    def get_demo_action(self, page_state: dict) -> dict:
        """Demo mode heuristic: simple rule-based action selection."""
        visible_text = page_state.get("visible_text", "").lower()
        url = page_state.get("url", "")
        title = page_state.get("title", "")
        elements = page_state.get("interactive_elements", [])
        goal = page_state.get("goal", "").lower()
        goal_original = page_state.get("goal", "")

        # Extract URL from goal (e.g., "Go to example.com and tell me...")
        import re
        url_match = re.search(r'(?:go to|navigate to|open|visit)\s+(\S+(?:\.\S+)?)', goal)
        target_url = url_match.group(1) if url_match else None

        # If on about:blank and goal specifies a URL, navigate there
        if ("about:blank" in url or not url or url == "about:blank") and target_url:
            if not target_url.startswith("http"):
                target_url = "https://" + target_url
            return {
                "action": "navigate",
                "params": {"url": target_url},
                "reasoning": f"Navigating to {target_url} as specified in goal.",
            }

        # If on example.com, extract title and done
        if "example.com" in url or "example" in title.lower():
            return {
                "action": "done",
                "params": {"result": f"Page title: {title}. URL: {url}"},
                "reasoning": "On example page, task complete.",
            }

        # If goal mentions search and there's a search input
        if "search" in goal or "find" in goal or "look" in goal:
            for el in elements:
                sel = el.get("selector", "")
                tag = el.get("tag", "")
                el_type = el.get("type", "")
                name = el.get("name", "").lower()
                if tag == "input" and ("search" in name or "q" in name or "query" in name):
                    search_term = goal.replace("search for", "").replace("search", "").replace("find", "").strip()
                    if not search_term:
                        search_term = goal
                    return {
                        "action": "type",
                        "params": {"selector": sel, "text": search_term[:100]},
                        "reasoning": f"Typing search term into input: {name}",
                    }
                if tag == "input" and ("search" in el_type or "text" in el_type):
                    return {
                        "action": "type",
                        "params": {"selector": sel, "text": goal[:100]},
                        "reasoning": f"Typing into search input: {name}",
                    }

        # If there are buttons, click the most relevant one
        for el in elements:
            sel = el.get("selector", "")
            tag = el.get("tag", "")
            text = el.get("text", "").lower()
            if tag == "button" and ("search" in text or "go" in text or "submit" in text):
                return {
                    "action": "click",
                    "params": {"selector": sel},
                    "reasoning": f"Clicking button: {text}",
                }

        # If no elements to interact with, extract text
        if visible_text:
            return {
                "action": "done",
                "params": {"result": f"Page title: {title}. Content: {visible_text[:500]}"},
                "reasoning": "No clear interaction needed, returning visible content.",
            }

        return {
            "action": "wait",
            "params": {"seconds": 2},
            "reasoning": "Waiting for page to load.",
        }
