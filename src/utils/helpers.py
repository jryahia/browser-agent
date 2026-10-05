"""Helper utilities for formatting, truncation, and file operations."""

import re


def truncate_text(text: str, max_length: int = 3000) -> str:
    """Truncate text to max_length, preserving word boundaries."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    # Truncate at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]
    return truncated + "... [truncated]"


def format_page_state(page_state: dict) -> str:
    """Format page state for LLM prompt ingestion."""
    lines = []

    lines.append(f"CURRENT_URL: {page_state.get('url', 'N/A')}")
    lines.append(f"PAGE_TITLE: {page_state.get('title', 'N/A')}")
    lines.append("")

    visible_text = page_state.get("visible_text", "")
    if visible_text:
        lines.append("VISIBLE_TEXT (truncated):")
        lines.append(truncate_text(visible_text, 2000))
        lines.append("")

    elements = page_state.get("interactive_elements", [])
    if elements:
        lines.append("INTERACTIVE_ELEMENTS:")
        for i, el in enumerate(elements, 1):
            parts = []
            parts.append(f"[{i}] <{el.get('tag', '?')}>")
            if el.get("text"):
                text = el["text"][:60]
                parts.append(f'text="{text}"')
            if el.get("selector"):
                parts.append(f'selector="{el["selector"]}"')
            if el.get("type"):
                parts.append(f'type="{el["type"]}"')
            if el.get("name"):
                parts.append(f'name="{el["name"]}"')
            if el.get("href"):
                parts.append(f'href="{el["href"]}"')
            if el.get("placeholder"):
                parts.append(f'placeholder="{el["placeholder"]}"')
            if el.get("options"):
                parts.append(f'options="{el["options"]}"')
            lines.append("  ".join(parts))
        lines.append("")

    # Stuck warning
    if page_state.get("stuck"):
        lines.append("WARNING: You appear to be stuck. Try a different approach (e.g., navigate to a different URL).")
        lines.append("")

    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe for filenames."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()
