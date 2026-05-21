"""Parse LLM action responses."""

import re
import json
from typing import Optional


class ActionParser:
    """Parses LLM responses into structured actions."""

    VALID_ACTIONS = {
        "navigate", "click", "type", "select",
        "scroll", "extract", "wait", "screenshot", "done",
    }

    @classmethod
    def parse(cls, llm_response: Optional[str]) -> Optional[dict]:
        """Parse an LLM response string into an action dict.

        Returns:
            dict with keys: action, params, reasoning
            or None if parsing fails.
        """
        if not llm_response or not llm_response.strip():
            return None

        cleaned = llm_response.strip()

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(1).strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(cleaned)
            return cls._validate(parsed)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object with regex (handles extra text)
        obj_match = re.search(r"\{[^{}]*\"action\"[^{}]*\}", cleaned, re.DOTALL)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group(0))
                return cls._validate(parsed)
            except json.JSONDecodeError:
                pass

        # Try to extract action=... pattern (fallback)
        action_match = re.search(r'action["\']?\s*[:=]\s*["\'](\w+)["\']', cleaned)
        if action_match:
            action = action_match.group(1)
            if action in cls.VALID_ACTIONS:
                return {
                    "action": action,
                    "params": {},
                    "reasoning": "Parsed from LLM response (regex fallback).",
                }

        return None

    @classmethod
    def _validate(cls, parsed: dict) -> Optional[dict]:
        """Validate and normalize a parsed action dict."""
        action = parsed.get("action", "").strip().lower()
        if action not in cls.VALID_ACTIONS:
            return None

        params = parsed.get("params", {})
        if not isinstance(params, dict):
            params = {}

        reasoning = parsed.get("reasoning", "")
        if not isinstance(reasoning, str):
            reasoning = str(reasoning)

        return {
            "action": action,
            "params": params,
            "reasoning": reasoning,
        }
