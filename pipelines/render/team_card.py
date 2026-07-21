"""Top-level team card render entrypoint: build a CardModel, render it to
HTML, and screenshot it to a PNG via Playwright's headless Chromium
(already a project dependency — see pyproject.toml).
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pipelines.render import data_source, template
from pipelines.render.data_source import CardModel

DEFAULT_VIEWPORT_WIDTH = 1200
DEFAULT_VIEWPORT_HEIGHT = 900

# The environment's pre-installed Chromium build (see /opt/pw-browsers) may
# trail the pinned playwright package's expected browser revision; the
# stable "chromium" symlink there always resolves to a working binary
# regardless of that skew, so prefer it over Playwright's own revision
# lookup when present.
_PREINSTALLED_CHROMIUM = "/opt/pw-browsers/chromium"


def render(
    card: CardModel,
    output_path: Path,
    *,
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
) -> None:
    """Render card to a PNG at output_path."""
    html = template.render_html(card)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    launch_kwargs = {}
    if os.path.exists(_PREINSTALLED_CHROMIUM):
        launch_kwargs["executable_path"] = _PREINSTALLED_CHROMIUM
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            page.set_content(html, wait_until="load")
            page.locator(".card-wrap").screenshot(path=str(output_path))
        finally:
            browser.close()


def render_for_team(team_id: str, output_path: Path, **kwargs) -> None:
    card = data_source.load_from_team_id(team_id)
    render(card, output_path, **kwargs)


def render_for_spec(spec_path: Path, output_path: Path, **kwargs) -> None:
    card = data_source.load_from_spec(spec_path)
    render(card, output_path, **kwargs)
