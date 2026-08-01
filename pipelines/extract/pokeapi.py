"""PokéAPI extraction.

Contract: data/staging/pokeapi.schema.json,
data/staging/pokeapi_move.schema.json,
data/staging/pokeapi_ability.schema.json,
data/staging/pokeapi_item.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > PokéAPI"

Captures Pokémon/form identity rows and base stat rows, weekly refresh
cadence. Fetches every entry in PokéAPI's `/pokemon` list — base species
plus Mega/regional/alternate forms (e.g. `charizard-mega-x`,
`raichu-alola`) — not just the base national-dex range, so that
form-specific rows from OP.GG and MunchStats have a canonical row to join
against (dataset-spec.md's "Multi-form species that need explicit mapping
rather than name-only joins" known risk).

`pokemon_id` is the species' National Dex number, read from each form's
`species.url` rather than the form's own PokéAPI resource id — the latter
is an internal, non-dex id for alt forms (e.g. `charizard-mega-x` is
resource id 10034 but species id 6), and `pokemon_id` must stay the shared
identifier across all forms of one species. `form_name` is the form's own
PokéAPI slug (equal to the species name for the default/base form).
`type_1`/`type_2` (type_2 nullable) come off the same `/pokemon/{form}`
payload already fetched for stats, so adding them costs no extra HTTP call.

`extract_moves`/`extract_abilities`/`extract_items` are separate functions
writing separate staging files (move/ability/item grain, not
Pokémon/form grain) — added for the dashboard's Pokémon Profile
descriptions and Matchup-tab damage calculator (docs/todo.md M6 backlog:
"type-effectiveness / head-to-head matchups"). Each is scoped to an
explicit iterable of names (the moves/abilities/items actually reported in
MunchStats tournament roster data — `data/staging/munchstats.csv`'s
`moves`/`ability`/`item_name` fields) rather than PokéAPI's full
~900-move/~370-item catalog, since the dashboard only ever needs detail
for names that already appear in real tournament roster data.
"""

from __future__ import annotations

import csv
import sys
import time
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
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

MOVE_FIELDNAMES = [
    "move_name",
    "move_type",
    "power",
    "accuracy",
    "category",
    "priority",
    "pp",
    "short_effect",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

ABILITY_FIELDNAMES = [
    "ability_name",
    "short_effect",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]

ITEM_FIELDNAMES = [
    "item_name",
    "short_effect",
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


def _types(payload: dict) -> tuple[str, str | None]:
    ordered = sorted(payload["types"], key=lambda entry: entry["slot"])
    names = [entry["type"]["name"] for entry in ordered]
    type_1 = names[0]
    type_2 = names[1] if len(names) > 1 else None
    return type_1, type_2


def _row_from_payload(payload: dict, *, extracted_at_utc: str, dataset_version: str) -> dict:
    form_name = payload["name"]
    stats = {
        _STAT_NAME_TO_FIELD[entry["stat"]["name"]]: entry["base_stat"]
        for entry in payload["stats"]
        if entry["stat"]["name"] in _STAT_NAME_TO_FIELD
    }
    type_1, type_2 = _types(payload)
    return {
        "pokemon_id": _species_id(payload),
        "pokemon_name": payload["species"]["name"],
        "form_name": form_name,
        **stats,
        "stat_total": sum(stats.values()),
        "type_1": type_1,
        "type_2": type_2,
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


def _slugify(display_name: str) -> str:
    """PokéAPI resource slugs are lowercase-hyphenated (e.g. "Choice Band"
    -> "choice-band", "King's Rock" -> "kings-rock"); dashboard-facing move/
    item/ability names elsewhere in this pipeline are Title Case (see
    dbt/seeds/pokeapi_move_types.csv's "move display name, Title Case"
    convention), so both directions are needed at the extraction boundary.

    Strips both the straight apostrophe (') and the Unicode right/left
    single quotation marks (’/‘) some real tournament roster text
    uses in place of a straight apostrophe (e.g. "King’s Shield") — left
    unstripped, the curly form survives into the URL as a percent-encoded
    byte sequence PokéAPI's router 400s on, rather than resolving the same
    as the straight-apostrophe form.
    """
    return display_name.lower().replace("'", "").replace("’", "").replace("‘", "").replace(" ", "-")


def _english_short_effect(payload: dict) -> str | None:
    for entry in payload.get("effect_entries", []):
        if entry["language"]["name"] == "en":
            return " ".join(entry["short_effect"].split())
    return None


def _fetch_resource(session: requests.Session, resource: str, slug: str) -> dict:
    url = f"{API_BASE_URL}/{resource}/{slug}"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


_TRANSIENT_RETRY_ATTEMPTS = 3
_TRANSIENT_RETRY_DELAY_SECONDS = 2.0


def _fetch_resource_or_none(session: requests.Session, resource: str, slug: str) -> dict | None:
    """Like _fetch_resource, but returns None instead of raising when a
    single move/ability/item can't be fetched, rather than aborting
    extraction for every other name:
    - A 404 means the name doesn't resolve to any PokéAPI resource (a
      genuine data-quality issue in the upstream source, e.g. a truncated
      move name) — returns None immediately, no retry.
    - A transient error (5xx, connection/timeout) is retried a few times
      with a short delay, then treated the same as a 404 (skip, don't
      crash the whole run) if it never recovers — a single flaky response
      out of hundreds of lookups shouldn't lose everything else already
      fetched.
    """
    last_exc: Exception | None = None
    for attempt in range(_TRANSIENT_RETRY_ATTEMPTS):
        try:
            return _fetch_resource(session, resource, slug)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return None
            last_exc = exc
        except requests.exceptions.RequestException as exc:
            last_exc = exc
        if attempt < _TRANSIENT_RETRY_ATTEMPTS - 1:
            time.sleep(_TRANSIENT_RETRY_DELAY_SECONDS)
    print(
        f"Giving up on {resource}/{slug} after {_TRANSIENT_RETRY_ATTEMPTS} attempts: {last_exc}",
        file=sys.stderr,
    )
    return None


def extract_moves(
    output_path: Path,
    move_names: Iterable[str],
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch PokéAPI move detail (type/power/accuracy/category/priority/pp/
    short_effect) for the given display names and write them to output_path
    as CSV matching data/staging/pokeapi_move.schema.json.

    Scoped to an explicit iterable (the moves actually referenced by
    tournament roster data) rather than PokéAPI's full move catalog.
    """
    http = session if session is not None else requests.Session()
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for move_name in move_names:
        slug = _slugify(move_name)
        payload = _fetch_resource_or_none(http, "move", slug)
        if payload is None:
            print(f"Skipping unresolved move: {move_name!r} (slug {slug!r})", file=sys.stderr)
            continue
        rows.append(
            {
                "move_name": move_name,
                "move_type": payload["type"]["name"],
                "power": payload["power"],
                "accuracy": payload["accuracy"],
                "category": payload["damage_class"]["name"],
                "priority": payload["priority"],
                "pp": payload["pp"],
                "short_effect": _english_short_effect(payload),
                "source_name": SOURCE_NAME,
                "source_url": f"{API_BASE_URL}/move/{slug}",
                "source_record_id": str(payload["id"]),
                "extracted_at_utc": extracted_at_utc,
                "dataset_version": dataset_version,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MOVE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def extract_abilities(
    output_path: Path,
    ability_names: Iterable[str],
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch PokéAPI ability effect text for the given display names and
    write them to output_path as CSV matching
    data/staging/pokeapi_ability.schema.json.
    """
    http = session if session is not None else requests.Session()
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for ability_name in ability_names:
        slug = _slugify(ability_name)
        payload = _fetch_resource_or_none(http, "ability", slug)
        if payload is None:
            print(f"Skipping unresolved ability: {ability_name!r} (slug {slug!r})", file=sys.stderr)
            continue
        rows.append(
            {
                "ability_name": ability_name,
                "short_effect": _english_short_effect(payload),
                "source_name": SOURCE_NAME,
                "source_url": f"{API_BASE_URL}/ability/{slug}",
                "source_record_id": str(payload["id"]),
                "extracted_at_utc": extracted_at_utc,
                "dataset_version": dataset_version,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ABILITY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def extract_items(
    output_path: Path,
    item_names: Iterable[str],
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch PokéAPI held-item effect text for the given display names and
    write them to output_path as CSV matching
    data/staging/pokeapi_item.schema.json.
    """
    http = session if session is not None else requests.Session()
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for item_name in item_names:
        slug = _slugify(item_name)
        payload = _fetch_resource_or_none(http, "item", slug)
        if payload is None:
            print(f"Skipping unresolved item: {item_name!r} (slug {slug!r})", file=sys.stderr)
            continue
        rows.append(
            {
                "item_name": item_name,
                "short_effect": _english_short_effect(payload),
                "source_name": SOURCE_NAME,
                "source_url": f"{API_BASE_URL}/item/{slug}",
                "source_record_id": str(payload["id"]),
                "extracted_at_utc": extracted_at_utc,
                "dataset_version": dataset_version,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ITEM_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
