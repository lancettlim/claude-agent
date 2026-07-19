"""PokéBase app extraction.

Contract: data/staging/pokebase.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > PokéBase"

Captures per-regulation legal-pool membership for Pokémon Champions from
pokebase.app/pokemon-champions/pokemon. Like OP.GG's Champions Pokédex page
(see pipelines/extract/opgg.py's docstring), this is server-rendered by
Next.js and ships its full paginated pokemon list (a `docs` array, 1360
entries, single page — `hasNextPage: false`) as a JSON payload embedded in
a React Server Components "Flight" script chunk
(`self.__next_f.push([1, "..."])`), so a plain HTTP GET is enough despite
the page appearing JS-driven; no browser automation is required.
`_extract_pokemon_payloads` locates and unescapes it using the same
technique as opgg.py.

Each pokemon entry that's part of the Champions legal pool carries a
`regulationSets` array (e.g. `[{"name": "M-A", "slug": "m-a", ...}]`)
naming every regulation it's legal under; entries with no `regulationSets`
field aren't currently in the legal pool and are skipped. One staging row
is emitted per (pokemon, regulation) pair. `nationalNumber` is PokéBase's
own National Dex field and is correct for Mega/regional/alternate forms
too (unlike OP.GG's fabricated per-form ids), so it's used directly as
`pokemon_id`. `slug` already follows PokéAPI's own form-naming convention
for the large majority of entries (e.g. `charizard-mega-x`); the handful
that don't (bare species names PokéAPI splits into named sub-forms with no
default-equals-species-name entry) are resolved downstream by the
pokebase_slug_to_pokeapi_form seed, same as OP.GG/MunchStats.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_NAME = "PokéBase"
PAGE_URL = "https://pokebase.app/pokemon-champions/pokemon"
DEFAULT_DATASET_VERSION = "0.0.0-dev"

FIELDNAMES = [
    "pokemon_id",
    "pokemon_name",
    "form_name",
    "regulation_code",
    "is_legal",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

_ARRAY_MARKER = '\\"data\\":{\\"docs\\":['


def _fetch_page_html(session: requests.Session) -> str:
    response = session.get(PAGE_URL, timeout=30)
    response.raise_for_status()
    return response.text


def _find_array_end(text: str, open_bracket_index: int) -> int:
    """Scan forward from an opening `[` to its matching `]`, treating the
    escaped-quote sequence `\\"` as a single quote-toggle token so brackets
    inside string values aren't counted."""
    depth = 0
    in_string = False
    i = open_bracket_index
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] == '"':
            in_string = not in_string
            i += 2
            continue
        if not in_string:
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise ValueError("Unbalanced brackets while scanning embedded pokemon payload")


def _extract_pokemon_payloads(html: str) -> list[dict]:
    marker_index = html.find(_ARRAY_MARKER)
    if marker_index == -1:
        raise ValueError("Could not find embedded pokemon payload in PokéBase page HTML")
    array_start = marker_index + len(_ARRAY_MARKER) - 1
    array_end = _find_array_end(html, array_start)
    escaped_array = html[array_start : array_end + 1]
    unescaped_array = json.loads(f'"{escaped_array}"')
    return json.loads(unescaped_array)


def _rows_from_pokemon(payload: dict, *, extracted_at_utc: str, dataset_version: str) -> list[dict]:
    rows = []
    for regulation in payload.get("regulationSets") or []:
        rows.append(
            {
                "pokemon_id": payload["nationalNumber"],
                "pokemon_name": payload["name"],
                "form_name": payload["slug"],
                "regulation_code": regulation["slug"],
                "is_legal": True,
                "source_name": SOURCE_NAME,
                "source_url": f"{PAGE_URL}/{payload['slug']}",
                "source_record_id": f"{payload['id']}:{regulation['id']}",
                "extracted_at_utc": extracted_at_utc,
                "dataset_version": dataset_version,
            }
        )
    return rows


def extract(
    output_path: Path,
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch the PokéBase Champions Pokédex page, extract its embedded
    per-regulation legal-pool membership, and write it to output_path as
    CSV matching the field list in data/staging/pokebase.schema.json,
    including provenance fields."""
    http = session if session is not None else requests.Session()
    html = _fetch_page_html(http)
    payloads = _extract_pokemon_payloads(html)
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for payload in payloads:
        rows.extend(
            _rows_from_pokemon(
                payload, extracted_at_utc=extracted_at_utc, dataset_version=dataset_version
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
