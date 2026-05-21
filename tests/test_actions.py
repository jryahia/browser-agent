"""Tests for action executor."""

import pytest


class TestActionParser:
    """Test the action parser from llm module."""

    def test_parse_valid_json(self):
        from src.llm.parser import ActionParser

        response = '{"action": "click", "params": {"selector": "#btn"}, "reasoning": "test"}'
        result = ActionParser.parse(response)
        assert result is not None
        assert result["action"] == "click"
        assert result["params"]["selector"] == "#btn"

    def test_parse_markdown_code_block(self):
        from src.llm.parser import ActionParser

        response = '```json\n{"action": "navigate", "params": {"url": "https://example.com"}, "reasoning": "go"}\n```'
        result = ActionParser.parse(response)
        assert result is not None
        assert result["action"] == "navigate"
        assert result["params"]["url"] == "https://example.com"

    def test_parse_invalid_action(self):
        from src.llm.parser import ActionParser

        response = '{"action": "fly", "params": {}, "reasoning": "test"}'
        result = ActionParser.parse(response)
        assert result is None

    def test_parse_empty_response(self):
        from src.llm.parser import ActionParser

        assert ActionParser.parse("") is None
        assert ActionParser.parse(None) is None

    def test_parse_done_action(self):
        from src.llm.parser import ActionParser

        response = '{"action": "done", "params": {"result": "Task complete"}, "reasoning": "finished"}'
        result = ActionParser.parse(response)
        assert result is not None
        assert result["action"] == "done"


class TestSystemPrompt:
    """Test the system prompt builder."""

    def test_build_includes_max_steps(self):
        from src.llm.prompts import SystemPromptBuilder

        prompt = SystemPromptBuilder.build(max_steps=15)
        assert "15" in prompt
        assert "BrowserBot" in prompt

    def test_build_default(self):
        from src.llm.prompts import SystemPromptBuilder

        prompt = SystemPromptBuilder.build()
        assert "30" in prompt


class TestHelpers:
    """Test utility helpers."""

    def test_truncate_text(self):
        from src.utils.helpers import truncate_text

        short = "Hello world"
        assert truncate_text(short, 100) == short

        long = "a" * 5000
        assert len(truncate_text(long, 100)) <= 120  # allow for "... [truncated]"

    def test_sanitize_filename(self):
        from src.utils.helpers import sanitize_filename

        assert sanitize_filename("hello/world:test") == "hello_world_test"
        assert sanitize_filename("safe_name") == "safe_name"

    def test_format_page_state(self):
        from src.utils.helpers import format_page_state

        state = {
            "url": "https://example.com",
            "title": "Example",
            "visible_text": "Hello world",
            "interactive_elements": [
                {"tag": "a", "text": "Click me", "selector": "a.link", "href": "/page"}
            ],
        }
        formatted = format_page_state(state)
        assert "https://example.com" in formatted
        assert "Example" in formatted
        assert "Click me" in formatted
        assert "a.link" in formatted
