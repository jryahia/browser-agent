"""Session persistence — save/load browser state (cookies, localStorage)."""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages browser session persistence across tasks."""

    def __init__(self, session_dir: str = ".browser_sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id: Optional[str] = None

    def _session_path(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"

    async def save_state(self, context, session_id: str):
        """Save cookies and localStorage to disk."""
        try:
            cookies = await context.cookies()
            state = {"cookies": cookies, "session_id": session_id}
            path = self._session_path(session_id)
            path.write_text(json.dumps(state, indent=2))
            self.current_session_id = session_id
        except Exception as e:
            logger.warning("Failed to save session state: %s", e)

    async def load_state(self, context, session_id: str) -> bool:
        """Load cookies into browser context. Returns True if state was found."""
        path = self._session_path(session_id)
        if not path.exists():
            return False
        try:
            state = json.loads(path.read_text())
            cookies = state.get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)
            self.current_session_id = session_id
            return True
        except Exception as e:
            logger.warning("Failed to load session state: %s", e)
            return False

    def list_sessions(self) -> list[str]:
        """List saved session IDs."""
        return [p.stem for p in self.session_dir.glob("*.json")]

    def delete_session(self, session_id: str):
        """Delete a saved session."""
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
