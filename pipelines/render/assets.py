"""Type/item icon assets for team card rendering.

These are rendering-support assets, not dataset entities — they carry no
provenance row, no dataset_version, no release gate (see docs/dataset-
spec.md's "pokemon_asset" entity, which is the actual dataset entity for
Pokémon sprites; type/item icons are consumed here directly instead).

Icons come from the PokéAPI community sprites GitHub repo
(github.com/PokeAPI/sprites), referenced descriptively in
docs/data-sources.md's PokéAPI entry but not previously fetched by any code
in this repo. Files are stable, deterministically-named raw GitHub URLs, so
a plain cache-then-download-on-miss helper is enough — no discovery/listing
call is needed the way Bulbagarden's MediaWiki category API is.
"""

from __future__ import annotations

from pathlib import Path

import requests

TYPE_ICON_BASE_URL = (
    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/types/"
    "generation-ix/scarlet-violet"
)
ITEM_ICON_BASE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items"

# Order matches PokéAPI's own type IDs (1-indexed; see types.csv in
# github.com/PokeAPI/pokeapi's data/v2/csv), because PokeAPI/sprites' type
# icon files are named by numeric type ID, not type name (confirmed live:
# .../generation-ix/scarlet-violet/1.png is normal, /11.png is water, etc.)
TYPE_NAMES = [
    "normal",
    "fighting",
    "flying",
    "poison",
    "ground",
    "rock",
    "bug",
    "ghost",
    "steel",
    "fire",
    "water",
    "grass",
    "electric",
    "psychic",
    "ice",
    "dragon",
    "dark",
    "fairy",
]


def slugify(name: str) -> str:
    """Lowercase, hyphen-separated slug matching PokéAPI/sprites' item file
    naming convention (e.g. "Choice Scarf" -> "choice-scarf")."""
    return name.strip().lower().replace(" ", "-").replace("'", "")


def _download(session: requests.Session, url: str, dest_path: Path) -> None:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(response.content)


def ensure_type_icon(
    type_name: str,
    *,
    cache_dir: Path,
    session: requests.Session | None = None,
) -> Path | None:
    """Return a local cached path to type_name's icon, downloading it on a
    cache miss. Returns None (rather than raising) if type_name isn't a
    recognized type or the download fails, so a bad/missing/unreachable
    icon degrades gracefully in the renderer (a plain colored swatch,
    see template.py's TYPE_COLORS) instead of failing the whole card."""
    slug = type_name.strip().lower()
    if slug not in TYPE_NAMES:
        return None
    type_id = TYPE_NAMES.index(slug) + 1
    dest_path = cache_dir / "types" / f"{slug}.png"
    if not dest_path.exists():
        http = session if session is not None else requests.Session()
        try:
            _download(http, f"{TYPE_ICON_BASE_URL}/{type_id}.png", dest_path)
        except requests.RequestException:
            return None
    return dest_path


def ensure_item_icon(
    item_name: str,
    *,
    cache_dir: Path,
    session: requests.Session | None = None,
) -> Path | None:
    """Return a local cached path to item_name's icon, downloading it on a
    cache miss. Returns None (rather than raising) if the download fails —
    not every held item has a sprite in the community repo, and a missing
    item icon shouldn't fail card rendering."""
    slug = slugify(item_name)
    dest_path = cache_dir / "items" / f"{slug}.png"
    if not dest_path.exists():
        http = session if session is not None else requests.Session()
        try:
            _download(http, f"{ITEM_ICON_BASE_URL}/{slug}.png", dest_path)
        except requests.RequestException:
            return None
    return dest_path
