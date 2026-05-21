"""Page observation — extract DOM state from Playwright page."""

from typing import Optional


class PageObserver:
    """Observes and extracts page state from a Playwright page."""

    MAX_VISIBLE_TEXT_LENGTH = 3000
    MAX_ELEMENTS = 50

    def __init__(self, page):
        self.page = page

    async def observe(self) -> dict:
        """Extract current page state.

        Returns:
            dict with keys: url, title, visible_text, interactive_elements
        """
        url = self.page.url
        title = await self.page.title()
        visible_text = await self._get_visible_text()
        interactive_elements = await self._get_interactive_elements()

        return {
            "url": url,
            "title": title,
            "visible_text": visible_text[:self.MAX_VISIBLE_TEXT_LENGTH],
            "interactive_elements": interactive_elements[:self.MAX_ELEMENTS],
        }

    async def _get_visible_text(self) -> str:
        """Extract visible text content from the page."""
        try:
            text = await self.page.evaluate("""
                () => {
                    const body = document.body;
                    if (!body) return '';
                    const clone = body.cloneNode(true);
                    // Remove script and style elements
                    const scripts = clone.querySelectorAll('script, style, noscript, svg, canvas');
                    scripts.forEach(el => el.remove());
                    return clone.innerText || '';
                }
            """)
            if not text:
                text = await self.page.inner_text("body")
            return text.strip() if text else ""
        except Exception:
            try:
                return (await self.page.inner_text("body")).strip()
            except Exception:
                return ""

    async def _get_interactive_elements(self) -> list[dict]:
        """Extract interactive elements with CSS selectors.

        Returns list of dicts: {selector, tag, text, type, name, href, id}
        """
        try:
            elements = await self.page.evaluate("""
                () => {
                    const results = [];

                    // Helper to build a CSS selector for an element
                    function buildSelector(el) {
                        if (el.id) return '#' + CSS.escape(el.id);
                        if (el.getAttribute('data-testid')) {
                            return '[data-testid="' + el.getAttribute('data-testid') + '"]';
                        }
                        // Build path using class + nth-child
                        let path = [];
                        let current = el;
                        while (current && current !== document.body) {
                            let segment = current.tagName.toLowerCase();
                            if (current.id) {
                                segment = '#' + CSS.escape(current.id);
                                path.unshift(segment);
                                break;
                            }
                            if (current.className && typeof current.className === 'string') {
                                const classes = current.className.trim().split(/\\s+/).filter(c => c);
                                if (classes.length > 0) {
                                    segment += '.' + classes.map(c => CSS.escape(c)).join('.');
                                }
                            }
                            // Add nth-child if needed for uniqueness
                            const parent = current.parentElement;
                            if (parent) {
                                const siblings = Array.from(parent.children).filter(
                                    s => s.tagName === current.tagName
                                );
                                if (siblings.length > 1) {
                                    const index = siblings.indexOf(current) + 1;
                                    segment += ':nth-child(' + index + ')';
                                }
                            }
                            path.unshift(segment);
                            current = current.parentElement;
                        }
                        return path.join(' > ');
                    }

                    // Collect buttons
                    document.querySelectorAll('button, a, input, select, textarea').forEach(el => {
                        // Only visible elements
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) return;
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') return;

                        const tag = el.tagName.toLowerCase();
                        const info = {
                            selector: buildSelector(el),
                            tag: tag,
                            text: (el.innerText || el.value || '').trim().slice(0, 100),
                            type: el.getAttribute('type') || '',
                            name: el.getAttribute('name') || el.getAttribute('aria-label') || '',
                            href: el.getAttribute('href') || '',
                            id: el.id || '',
                        };

                        // For inputs, include placeholder
                        if (tag === 'input') {
                            info.placeholder = el.getAttribute('placeholder') || '';
                        }
                        // For selects, include options
                        if (tag === 'select') {
                            const options = Array.from(el.options).map(o => o.text).join(', ');
                            info.options = options.slice(0, 200);
                        }

                        results.push(info);
                    });

                    return results;
                }
            """)
            return elements or []
        except Exception:
            return []
