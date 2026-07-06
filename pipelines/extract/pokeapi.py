"""PokéAPI extraction.

Contract: data/staging/pokeapi.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > PokéAPI"

Captures Pokémon/form identity rows and base stat rows, weekly refresh
cadence. PokéAPI numeric IDs are treated as the canonical `pokemon_id`
(dataset-spec.md, "Key rules"); `form_name` defaults to the species name
until multi-form mapping is implemented (tracked as a known risk in
dataset-spec.md).

The OP.GG-mapped Champions pool that should ultimately scope this extract
isn't available yet (OP.GG extraction is still unimplemented), so this
fetches all currently known species by default; narrowing to the mapped
pool is Phase 2 normalization work once both sources are joined.
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

# PokéAPI pokemon IDs run contiguously from 1; this covers all currently
# known species as of dataset-spec.md's last update.
DEFAULT_MAX_POKEMON_ID = 1025

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


def _fetch_pokemon(session: requests.Session, pokemon_id: int) -> dict:
    url = f"{API_BASE_URL}/pokemon/{pokemon_id}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _row_from_payload(payload: dict, *, extracted_at_utc: str, dataset_version: str) -> dict:
    pokemon_id = payload["id"]
    stats = {
        _STAT_NAME_TO_FIELD[entry["stat"]["name"]]: entry["base_stat"]
        for entry in payload["stats"]
        if entry["stat"]["name"] in _STAT_NAME_TO_FIELD
    }
    return {
        "pokemon_id": pokemon_id,
        "pokemon_name": payload["name"],
        "form_name": payload["name"],
        **stats,
        "stat_total": sum(stats.values()),
        "source_name": SOURCE_NAME,
        "source_url": f"{API_BASE_URL}/pokemon/{pokemon_id}",
        "source_record_id": str(pokemon_id),
        "extracted_at_utc": extracted_at_utc,
        "dataset_version": dataset_version,
    }


def extract(
    output_path: Path,
    pokemon_ids: Iterable[int] | None = None,
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch PokéAPI identity + base stat rows and write them to output_path
    as CSV matching the field list in data/staging/pokeapi.schema.json,
    including provenance fields (source_name, source_url, source_record_id,
    extracted_at_utc, dataset_version).

    `pokemon_ids` defaults to 1..DEFAULT_MAX_POKEMON_ID (all known species);
    pass an explicit iterable to scope the extract, e.g. to a mapped pool.
    """
    ids = pokemon_ids if pokemon_ids is not None else range(1, DEFAULT_MAX_POKEMON_ID + 1)
    http = session if session is not None else requests.Session()
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = [
        _row_from_payload(
            _fetch_pokemon(http, pokemon_id),
            extracted_at_utc=extracted_at_utc,
            dataset_version=dataset_version,
        )
        for pokemon_id in ids
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
