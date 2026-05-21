"""Tests for agent module."""

import pytest


class TestLLMClient:
    """Test LLM client initialization."""

    def test_init_openai_default(self):
        from src.llm.client import LLMClient

        client = LLMClient(provider="openai")
        assert client.provider == "openai"
        assert client.model == "gpt-4o-mini"

    def test_init_deepseek(self):
        from src.llm.client import LLMClient

        client = LLMClient(provider="deepseek")
        assert client.provider == "deepseek"
        assert "deepseek" in client.base_url

    def test_init_anthropic(self):
        from src.llm.client import LLMClient

        client = LLMClient(provider="anthropic")
        assert client.provider == "anthropic"
        assert "claude" in client.model

    def test_demo_mode_without_key(self):
        from src.llm.client import LLMClient

        client = LLMClient(provider="openai", api_key="")
        assert client.demo_mode is True

    def test_demo_action(self):
        from src.llm.client import LLMClient

        client = LLMClient(provider="openai", api_key="")
        page_state = {
            "url": "https://example.com",
            "title": "Example Domain",
            "visible_text": "This domain is for use in illustrative examples",
            "interactive_elements": [],
            "goal": "Go to example.com and tell me the page title",
        }
        action = client.get_demo_action(page_state)
        assert action["action"] == "done"
        assert "Example" in action["params"]["result"]


class TestStealthConfig:
    """Test stealth configuration."""

    def test_random_user_agent(self):
        from src.stealth.config import StealthConfig

        config = StealthConfig()
        ua = config.random_user_agent()
        assert "Mozilla" in ua
        assert "Chrome" in ua or "Firefox" in ua

    def test_random_viewport(self):
        from src.stealth.config import StealthConfig

        config = StealthConfig()
        vp = config.random_viewport()
        assert "width" in vp
        assert "height" in vp
        assert vp["width"] >= 1280

    def test_random_delay(self):
        from src.stealth.config import StealthConfig

        delay = StealthConfig.random_delay(0.5, 2.0)
        assert 0.5 <= delay <= 2.0


class TestSessionManager:
    """Test session persistence."""

    def test_session_operations(self, tmp_path):
        from src.engine.session import SessionManager

        mgr = SessionManager(session_dir=str(tmp_path / "sessions"))
        assert mgr.list_sessions() == []

        # Save and load (no browser context here, just test paths)
        path = mgr._session_path("test123")
        assert path.name == "test123.json"
