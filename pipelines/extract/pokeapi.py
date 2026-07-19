"""PokéAPI extraction.

Contract: data/staging/pokeapi.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > PokéAPI"

Captures Pokémon/form identity rows, base stat rows, type(s), an
official-artwork image URL, and height/weight, weekly refresh cadence.
Fetches every entry in PokéAPI's `/pokemon` list — base species plus
Mega/regional/alternate forms (e.g. `charizard-mega-x`, `raichu-alola`) —
not just the base national-dex range, so that form-specific rows from
OP.GG and MunchStats have a canonical row to join against
(dataset-spec.md's "Multi-form species that need explicit mapping rather
than name-only joins" known risk).

`pokemon_id` is the species' National Dex number, read from each form's
`species.url` rather than the form's own PokéAPI resource id — the latter
is an internal, non-dex id for alt forms (e.g. `charizard-mega-x` is
resource id 10034 but species id 6), and `pokemon_id` must stay the shared
identifier across all forms of one species. `form_name` is the form's own
PokéAPI slug (equal to the species name for the default/base form).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_NAME = "PokéAPI"
API_BASE_URL = "https://pokeapi.co/api/v2"
DEFAULT_DATASET_VERSION = "0.0.0-dev"

# Large enough to cover PokéAPI's full /pokemon list (base species plus
# Mega/regional/alternate forms) in a single page.
_LIST_PAGE_SIZE = 5000

FIELDNAMES = [
    "pokemon_id",
    "pokemon_name",
    "form_name",
    "hp",
    "attack",
    "defense",
    "sp_attack",
    "sp_defense",
    "speed",
    "stat_total",
    "type_1",
    "type_2",
    "image_url",
    "height",
    "weight",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

_STAT_NAME_TO_FIELD = {
    "hp": "hp",
    "attack": "attack",
    "defense": "defense",
    "special-attack": "sp_attack",
    "special-defense": "sp_defense",
    "speed": "speed",
}


def _fetch_pokemon_list(session: requests.Session) -> list[str]:
    url = f"{API_BASE_URL}/pokemon?limit={_LIST_PAGE_SIZE}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return [entry["name"] for entry in response.json()["results"]]


def _fetch_pokemon(session: requests.Session, form_name: str) -> dict:
    url = f"{API_BASE_URL}/pokemon/{form_name}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _species_id(payload: dict) -> int:
    species_url = payload["species"]["url"]
    return int(species_url.rstrip("/").rsplit("/", 1)[-1])


def _official_artwork_url(payload: dict) -> str | None:
    # `or {}` guards against explicit `None` values at any level of this
    # path (some forms have `sprites.other.official-artwork` present but
    # null), not just missing keys — plain `.get(k, {})` doesn't catch that.
    sprites = payload.get("sprites") or {}
    other = sprites.get("other") or {}
    artwork = other.get("official-artwork") or {}
    return artwork.get("front_default")


def _row_from_payload(payload: dict, *, extracted_at_utc: str, dataset_version: str) -> dict:
    form_name = payload["name"]
    stats = {
        _STAT_NAME_TO_FIELD[entry["stat"]["name"]]: entry["base_stat"]
        for entry in payload["stats"]
        if entry["stat"]["name"] in _STAT_NAME_TO_FIELD
    }
    types_by_slot = {entry["slot"]: entry["type"]["name"] for entry in payload["types"]}
    return {
        "pokemon_id": _species_id(payload),
        "pokemon_name": payload["species"]["name"],
        "form_name": form_name,
        **stats,
        "stat_total": sum(stats.values()),
        "type_1": types_by_slot.get(1),
        "type_2": types_by_slot.get(2),
        "image_url": _official_artwork_url(payload),
        "height": payload["height"],
        "weight": payload["weight"],
        "source_name": SOURCE_NAME,
        "source_url": f"{API_BASE_URL}/pokemon/{form_name}",
        "source_record_id": str(payload["id"]),
        "extracted_at_utc": extracted_at_utc,
        "dataset_version": dataset_version,
    }


def extract(
    output_path: Path,
    pokemon_identifiers: Iterable[str | int] | None = None,
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch PokéAPI identity + base stat rows and write them to output_path
    as CSV matching the field list in data/staging/pokeapi.schema.json,
    including provenance fields (source_name, source_url, source_record_id,
    extracted_at_utc, dataset_version).

    `pokemon_identifiers` defaults to every entry in PokéAPI's `/pokemon`
    list (base species plus Mega/regional/alternate forms); pass an
    explicit iterable of names or ids to scope the extract.
    """
    http = session if session is not None else requests.Session()
    identifiers = (
        pokemon_identifiers if pokemon_identifiers is not None else _fetch_pokemon_list(http)
    )
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = [
        _row_from_payload(
            _fetch_pokemon(http, identifier),
            extracted_at_utc=extracted_at_utc,
            dataset_version=dataset_version,
        )
        for identifier in identifiers
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
