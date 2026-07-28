"""Builds the static analytics dashboard site (docs/dashboard/) from
data/marts/*.csv, per docs/prd.md's M6 milestone.

The dashboard is a self-contained static HTML/CSS/vanilla-JS page (Chart.js
via CDN, no backend, no build tooling) so it can be hosted for free on
GitHub Pages — see docs/dashboard.md. Data is baked into the page as an
inline `window.DASHBOARD_DATA = {...}` assignment rather than fetched from
a separate JSON file, so the page also works opened directly via file://
(fetch() of a local file is blocked by CORS there).

Pokémon sprites, move-type icons, and item icons are copied/resolved
alongside the HTML into output_dir/images/ (see pipelines/dashboard/
sprites.py and pipelines/render/assets.py) rather than inlined as base64,
to keep the committed HTML file small and its diffs readable. Species
sprites and type icons are purely local file copies (offline); item icons
are the one part of a dashboard build that needs network access, since
item names are data-dependent and not practical to bundle in advance — see
the fetch_icons parameter below.

The Team Builder tab's Pro Team Gallery (curated real tournament teams
rendered as broadcast-style cards) is likewise a local file copy, not a
network fetch or a Playwright render at build time — see
_load_reference_teams and docs/dashboard.md's "Pro Team Gallery" section
for how those card PNGs are produced ahead of time.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipelines.dashboard import data, sprites
from pipelines.render import assets as render_assets

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_ICONS_DIR = STATIC_DIR / "icons"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "dashboard"
DEFAULT_ITEM_ICON_CACHE_DIR = REPO_ROOT / "data" / "assets" / "dashboard_icons"
DEFAULT_REFERENCE_TEAMS_DIR = REPO_ROOT / "data" / "reference_teams"


def _make_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _safe_json(payload: dict[str, Any]) -> str:
    # Guard against a stray "</script>" in the data breaking out of the
    # inline <script> block it's embedded in.
    return json.dumps(payload, default=str).replace("<", "\\u003c")


def _referenced_pokemon_keys(marts: dict[str, list[dict[str, Any]]]) -> set[str]:
    keys: set[str] = set()
    for rows in marts.values():
        for row in rows:
            if row.get("pokemon_key"):
                keys.add(row["pokemon_key"])
            if row.get("partner_pokemon_key"):
                keys.add(row["partner_pokemon_key"])
            if row.get("pokemon_keys"):
                keys.update(row["pokemon_keys"].split("|"))
    return keys


def _copy_type_icons(output_dir: Path) -> dict[str, str]:
    """Copies the 18 committed move-type icons (pipelines/dashboard/static/
    icons/types/) into output_dir/images/icons/types/ and returns a
    {type_name: "images/icons/types/<type>.png"} map. Purely a local file
    copy — no network access, since types never change."""
    dest_dir = output_dir / "images" / "icons" / "types"
    dest_dir.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, str] = {}
    source_dir = STATIC_ICONS_DIR / "types"
    if not source_dir.exists():
        return resolved
    for source_path in sorted(source_dir.glob("*.png")):
        shutil.copyfile(source_path, dest_dir / source_path.name)
        resolved[source_path.stem] = f"images/icons/types/{source_path.name}"
    return resolved


def _resolve_item_icons(
    marts: dict[str, list[dict[str, Any]]],
    *,
    output_dir: Path,
    icon_cache_dir: Path,
    fetch_icons: bool,
) -> dict[str, str]:
    """Resolves an icon for each distinct item_name in pokemon_item_usage
    via pipelines.render.assets.ensure_item_icon (PokeAPI community sprites,
    cached to icon_cache_dir) and copies resolved icons into
    output_dir/images/icons/items/. Returns a {item_name: relative_path}
    map of what succeeded; unresolved items are simply absent, degrading to
    a text-only item name in the UI. When fetch_icons is False (offline
    builds, tests), no network calls are made and this returns {}."""
    item_names = sorted(
        {row["item_name"] for row in marts.get("pokemon_item_usage", []) if row.get("item_name")}
    )
    if not item_names or not fetch_icons:
        return {}

    dest_dir = output_dir / "images" / "icons" / "items"
    dest_dir.mkdir(parents=True, exist_ok=True)

    resolved: dict[str, str] = {}
    session = requests.Session()
    for item_name in item_names:
        source_path = render_assets.ensure_item_icon(
            item_name, cache_dir=icon_cache_dir, session=session
        )
        if not source_path or not source_path.exists():
            continue
        dest_path = dest_dir / source_path.name
        shutil.copyfile(source_path, dest_path)
        resolved[item_name] = f"images/icons/items/{source_path.name}"
    return resolved


def _load_reference_teams(output_dir: Path, reference_teams_dir: Path) -> list[dict[str, Any]]:
    """Pro Team Gallery feed (Team Builder tab): reads curated real-team
    metadata from reference_teams_dir/reference_teams.json and copies each
    entry's pre-rendered card PNG (reference_teams_dir/cards/<file>) into
    output_dir/images/reference_teams/. Cards are pre-rendered ahead of
    time via `render-card` (see docs/dashboard.md's "Pro Team Gallery"
    section) -- this function only copies already-built PNGs, so a
    dashboard build never needs Playwright/Chromium itself. Degrades to []
    (not an error) if the directory or metadata file doesn't exist yet,
    matching every other mart/asset's missing-input behavior."""
    metadata_path = reference_teams_dir / "reference_teams.json"
    if not metadata_path.exists():
        return []

    entries = json.loads(metadata_path.read_text(encoding="utf-8"))
    dest_dir = output_dir / "images" / "reference_teams"
    dest_dir.mkdir(parents=True, exist_ok=True)

    resolved: list[dict[str, Any]] = []
    for entry in entries:
        entry = dict(entry)
        card_image = entry.get("card_image")
        if card_image:
            source_path = reference_teams_dir / "cards" / card_image
            if source_path.exists():
                shutil.copyfile(source_path, dest_dir / source_path.name)
                entry["card_image"] = f"images/reference_teams/{source_path.name}"
            else:
                entry["card_image"] = None
        resolved.append(entry)
    return resolved


def build(
    *,
    marts_dir: Path = data.DEFAULT_MARTS_DIR,
    normalized_dir: Path = data.DEFAULT_NORMALIZED_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    asset_cache_dir: Path = sprites.DEFAULT_ASSET_CACHE_DIR,
    item_icon_cache_dir: Path = DEFAULT_ITEM_ICON_CACHE_DIR,
    reference_teams_dir: Path = DEFAULT_REFERENCE_TEAMS_DIR,
    fetch_icons: bool = True,
) -> dict[str, Any]:
    """Renders templates/index.html.jinja with the marts payload baked in,
    copies static/app.js alongside it, and populates output_dir/images/
    with Pokémon sprites, move-type icons, and item icons. Returns the
    payload that was rendered (including the sprite/icon maps).

    fetch_icons controls whether item icons are fetched over the network
    (see _resolve_item_icons); pass False for offline/test builds.
    """
    payload = data.build_payload(marts_dir, normalized_dir)

    referenced_keys = _referenced_pokemon_keys(payload["marts"])
    payload["sprites"] = sprites.copy_sprites(
        referenced_keys,
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=asset_cache_dir,
    )
    payload["type_icons"] = _copy_type_icons(output_dir)
    payload["item_icons"] = _resolve_item_icons(
        payload["marts"],
        output_dir=output_dir,
        icon_cache_dir=item_icon_cache_dir,
        fetch_icons=fetch_icons,
    )
    payload["reference_teams"] = _load_reference_teams(output_dir, reference_teams_dir)

    env = _make_environment()
    template = env.get_template("index.html.jinja")
    html = template.render(payload=payload, data_json=_safe_json(payload))

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    for script_name in ("app.js", "matchup.js", "teams.js"):
        shutil.copyfile(STATIC_DIR / script_name, output_dir / script_name)

    return payload
