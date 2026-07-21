"""Builds the static analytics dashboard site (docs/dashboard/) from
data/marts/*.csv, per docs/prd.md's M6 milestone.

The dashboard is a self-contained static HTML/CSS/vanilla-JS page (Chart.js
via CDN, no backend, no build tooling) so it can be hosted for free on
GitHub Pages — see docs/dashboard.md. Data is baked into the page as an
inline `window.DASHBOARD_DATA = {...}` assignment rather than fetched from
a separate JSON file, so the page also works opened directly via file://
(fetch() of a local file is blocked by CORS there).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipelines.dashboard import data

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "dashboard"


def _make_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _safe_json(payload: dict[str, Any]) -> str:
    # Guard against a stray "</script>" in the data breaking out of the
    # inline <script> block it's embedded in.
    return json.dumps(payload, default=str).replace("<", "\\u003c")


def build(
    *,
    marts_dir: Path = data.DEFAULT_MARTS_DIR,
    normalized_dir: Path = data.DEFAULT_NORMALIZED_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Renders templates/index.html.jinja with the marts payload baked in
    and copies static/app.js alongside it into output_dir. Returns the
    payload that was rendered."""
    payload = data.build_payload(marts_dir, normalized_dir)
    env = _make_environment()
    template = env.get_template("index.html.jinja")
    html = template.render(payload=payload, data_json=_safe_json(payload))

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    shutil.copyfile(STATIC_DIR / "app.js", output_dir / "app.js")

    return payload
