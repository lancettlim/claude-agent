"""OP.GG Pokémon Champions extraction.

Contract: data/staging/opgg_champions.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > OP.GG Pokémon Champions"

Captures legal pool membership and rebalanced stat values from
op.gg/pokemon-champions/pokedex, daily change detection.

The page is server-rendered by Next.js and ships its entire Pokédex dataset
(all legal-pool entries) as a JSON array embedded in a React Server
Components "Flight" script chunk (`self.__next_f.push([1, "..."])`), so a
plain HTTP GET is enough — no browser automation is required despite the
page appearing JS-driven in the DOM. The embedded array is JSON-string-
escaped once more than the page's own markup (every `"` becomes `\"`)
because it's nested inside that script chunk's string-literal argument;
`_extract_pokemon_payloads` locates it and undoes that extra layer of
escaping before parsing.

OP.GG's `id` field matches the real National Dex number for base-form
species but uses fabricated IDs (>=10000) for Mega/regional/alternate
forms, so `pokemon_id` is left null for those per the schema's "null if
only name/form mapping applies" contract. Regulation codes aren't published
on this page, so `regulation_code` is left blank — a known risk called out
in the schema contract (custom form labels / HTML structure volatility).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_NAME = "OP.GG Pokémon Champions"
PAGE_URL = "https://op.gg/pokemon-champions/pokedex"
DEFAULT_DATASET_VERSION = "0.0.0-dev"

# OP.GG fabricates IDs at and above this value for forms without a real
# National Dex number (Mega/regional/alternate forms); below it, `id`
# matches the canonical Pokédex number.
_FABRICATED_ID_THRESHOLD = 10000

FIELDNAMES = [
    "pokemon_id",
    "pokemon_name",
    "form_name",
    "is_legal",
    "hp",
    "attack",
    "defense",
    "sp_attack",
    "sp_defense",
    "speed",
    "stat_total",
    "regulation_code",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

_ARRAY_MARKER = '\\"pokemon\\":['


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
        raise ValueError("Could not find embedded pokemon payload in OP.GG page HTML")
    array_start = marker_index + len(_ARRAY_MARKER) - 1
    array_end = _find_array_end(html, array_start)
    escaped_array = html[array_start : array_end + 1]
    unescaped_array = json.loads(f'"{escaped_array}"')
    return json.loads(unescaped_array)


def _species_name(key: str) -> str:
    return key.replace("-", " ").title()


def _row_from_pokemon(payload: dict, *, extracted_at_utc: str, dataset_version: str) -> dict:
    key = payload["key"]
    raw_id = payload["id"]
    stats = payload["stats"]
    stat_fields = {
        "hp": stats["hp"],
        "attack": stats["attack"],
        "defense": stats["defense"],
        "sp_attack": stats["spAttack"],
        "sp_defense": stats["spDefense"],
        "speed": stats["speed"],
    }
    base_key = payload.get("base_key")
    return {
        "pokemon_id": raw_id if raw_id < _FABRICATED_ID_THRESHOLD else None,
        "pokemon_name": _species_name(base_key) if base_key else payload["name"],
        "form_name": payload["name"],
        "is_legal": True,
        **stat_fields,
        "stat_total": sum(stat_fields.values()),
        "regulation_code": "",
        "source_name": SOURCE_NAME,
        "source_url": f"{PAGE_URL}/{key}",
        "source_record_id": key,
        "extracted_at_utc": extracted_at_utc,
        "dataset_version": dataset_version,
    }


def extract(
    output_path: Path,
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch the OP.GG Champions Pokédex page, extract its embedded legal
    pool + rebalanced stat data, and write it to output_path as CSV
    matching the field list in data/staging/opgg_champions.schema.json,
    including provenance fields."""
    http = session if session is not None else requests.Session()
    html = _fetch_page_html(http)
    payloads = _extract_pokemon_payloads(html)
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = [
        _row_from_pokemon(
            payload, extracted_at_utc=extracted_at_utc, dataset_version=dataset_version
        )
        for payload in payloads
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
