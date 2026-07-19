"""MunchStats extraction.

Contract: data/staging/munchstats.schema.json
Spec reference: docs/dataset-spec.md, "Source-specific extraction contracts > MunchStats"

Pulls structured JSON from the MunchStats repo (github.com/PizzaTimeJoshua/munchstats)
via raw.githubusercontent.com and flattens nested team arrays into one row
per team member, per docs/data-sources.md's "How to extract" notes.

Repo layout (see the repo's README "Data Files" section):
  stats/tournaments/tournaments_index.json      one entry per scraped tournament
  stats/tournaments/{tournament_id}/metadata.json   event name/date/location/type
  stats/tournaments/{tournament_id}/players.json    list of {name, country,
      placement, team: [{pokemon, item, ability, tera_type, moves}, ...],
      day_reached, team_link, record}

MunchStats doesn't expose an opaque per-player ID or a separately reported
form label (forms like "Urshifu-Rapid-Strike" are embedded in `pokemon`
name) — both are known risks called out in the schema contract. `player_id`
is derived from a hash of the player's name and country; `form_name` is
left blank pending normalization.

`metadata.json`'s `type` (tournament tier, e.g. "International"/"Regional"),
`players.json`'s `record` (win/loss count), and team-member `item`/
`ability`/`tera_type`/`moves` are captured too, duplicated onto every
roster-slot row like `placement` already is; `moves` is a pipe-delimited
string since a roster slot can carry more than one.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_NAME = "MunchStats"
RAW_BASE_URL = "https://raw.githubusercontent.com/PizzaTimeJoshua/munchstats/main"
TOURNAMENTS_INDEX_URL = f"{RAW_BASE_URL}/stats/tournaments/tournaments_index.json"
DEFAULT_DATASET_VERSION = "0.0.0-dev"

FIELDNAMES = [
    "event_id",
    "event_name",
    "event_date",
    "event_tier",
    "team_id",
    "player_id",
    "placement",
    "record_wins",
    "record_losses",
    "slot_number",
    "pokemon_name",
    "form_name",
    "item_name",
    "ability",
    "tera_type",
    "moves",
    "source_name",
    "source_url",
    "source_record_id",
    "extracted_at_utc",
    "dataset_version",
]


def _tournament_dir_url(tournament_id: str) -> str:
    return f"{RAW_BASE_URL}/stats/tournaments/{tournament_id}"


def _fetch_json(session: requests.Session, url: str):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def _team_id(player: dict, tournament_id: str) -> str:
    team_link = player.get("team_link") or ""
    if team_link:
        return team_link.rstrip("/").rsplit("/", 1)[-1]
    return f"{tournament_id}:{player['name']}"


def _player_id(player: dict) -> str:
    basis = f"{player['name']}|{player.get('country', '')}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def _rows_for_tournament(
    session: requests.Session,
    tournament_id: str,
    *,
    extracted_at_utc: str,
    dataset_version: str,
) -> list[dict]:
    metadata = _fetch_json(session, f"{_tournament_dir_url(tournament_id)}/metadata.json")
    players = _fetch_json(session, f"{_tournament_dir_url(tournament_id)}/players.json")
    players_url = f"{_tournament_dir_url(tournament_id)}/players.json"

    rows = []
    for player in players:
        team_id = _team_id(player, tournament_id)
        player_id = _player_id(player)
        record = player.get("record") or {}
        for slot_number, member in enumerate(player.get("team", []), start=1):
            rows.append(
                {
                    "event_id": tournament_id,
                    "event_name": metadata["name"],
                    "event_date": metadata["date"],
                    "event_tier": metadata.get("type", ""),
                    "team_id": team_id,
                    "player_id": player_id,
                    "placement": player["placement"],
                    "record_wins": record.get("wins", ""),
                    "record_losses": record.get("losses", ""),
                    "slot_number": slot_number,
                    "pokemon_name": member["pokemon"],
                    "form_name": "",
                    "item_name": member.get("item", ""),
                    "ability": member.get("ability", ""),
                    "tera_type": member.get("tera_type", ""),
                    "moves": "|".join(member.get("moves", [])),
                    "source_name": SOURCE_NAME,
                    "source_url": players_url,
                    "source_record_id": f"{tournament_id}:{team_id}:{slot_number}",
                    "extracted_at_utc": extracted_at_utc,
                    "dataset_version": dataset_version,
                }
            )
    return rows


def extract(
    output_path: Path,
    tournament_ids: Iterable[str] | None = None,
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    session: requests.Session | None = None,
) -> None:
    """Fetch MunchStats tournament/team/roster JSON, flatten nested team
    arrays into one row per team member, and write to output_path as CSV
    matching the field list in data/staging/munchstats.schema.json,
    including provenance fields.

    `tournament_ids` defaults to every tournament in
    stats/tournaments/tournaments_index.json; pass an explicit iterable to
    scope the extract to specific events.
    """
    http = session if session is not None else requests.Session()
    ids = (
        tournament_ids
        if tournament_ids is not None
        else [entry["id"] for entry in _fetch_json(http, TOURNAMENTS_INDEX_URL)]
    )
    extracted_at_utc = datetime.now(timezone.utc).isoformat()

    rows = []
    for tournament_id in ids:
        rows.extend(
            _rows_for_tournament(
                http,
                tournament_id,
                extracted_at_utc=extracted_at_utc,
                dataset_version=dataset_version,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
