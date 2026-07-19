import csv

from pipelines.extract import munchstats


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payloads_by_url: dict[str, object]) -> None:
        self._payloads_by_url = payloads_by_url
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        return _FakeResponse(self._payloads_by_url[url])


TOURNAMENT_ID = "MB02w71HQZzTvTOYLtXb"
DIR_URL = munchstats._tournament_dir_url(TOURNAMENT_ID)

METADATA = {
    "id": TOURNAMENT_ID,
    "name": "2026 Melbourne Pokémon VGC Regional Championships",
    "date": "2026-05-23",
    "type": "Regional",
    "format": "gen9vgc2026regi",
}

PLAYERS = [
    {
        "name": "Nicholas Kan",
        "country": "AU",
        "placement": 1,
        "team": [
            {
                "pokemon": "Miraidon",
                "item": "Choice Specs",
                "ability": "Hadron Engine",
                "tera_type": "Fairy",
                "moves": ["Electro Drift", "Draco Meteor", "Protect", "Dazzling Gleam"],
            },
            {"pokemon": "Ursaluna", "item": "Flame Orb"},
        ],
        "day_reached": "top8",
        "team_link": f"/teamlist/public/{TOURNAMENT_ID}/YV8VbSG82iS8rMz0hhwb",
        "record": {"wins": 14, "losses": 2},
    },
    {
        "name": "No Link Player",
        "country": "US",
        "placement": 2,
        "team": [{"pokemon": "Incineroar", "item": "Assault Vest"}],
        "team_link": "",
    },
]


def _session_for_one_tournament():
    return _FakeSession(
        {
            munchstats.TOURNAMENTS_INDEX_URL: [{"id": TOURNAMENT_ID}],
            f"{DIR_URL}/metadata.json": METADATA,
            f"{DIR_URL}/players.json": PLAYERS,
        }
    )


def test_extract_flattens_team_into_one_row_per_slot(tmp_path):
    session = _session_for_one_tournament()
    output_path = tmp_path / "munchstats.csv"

    munchstats.extract(output_path, [TOURNAMENT_ID], dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 3  # 2 slots for player 1, 1 slot for player 2

    row = rows[0]
    assert row["event_id"] == TOURNAMENT_ID
    assert row["event_name"] == METADATA["name"]
    assert row["event_date"] == METADATA["date"]
    assert row["event_tier"] == "Regional"
    assert row["team_id"] == "YV8VbSG82iS8rMz0hhwb"
    assert row["placement"] == "1"
    assert row["record_wins"] == "14"
    assert row["record_losses"] == "2"
    assert row["slot_number"] == "1"
    assert row["pokemon_name"] == "Miraidon"
    assert row["form_name"] == ""
    assert row["item_name"] == "Choice Specs"
    assert row["ability"] == "Hadron Engine"
    assert row["tera_type"] == "Fairy"
    assert row["moves"] == "Electro Drift|Draco Meteor|Protect|Dazzling Gleam"
    assert row["source_name"] == "MunchStats"
    assert row["source_url"] == f"{DIR_URL}/players.json"
    assert row["source_record_id"] == f"{TOURNAMENT_ID}:YV8VbSG82iS8rMz0hhwb:1"
    assert row["dataset_version"] == "0.1.0"
    assert row["extracted_at_utc"]

    assert rows[1]["slot_number"] == "2"
    assert rows[1]["pokemon_name"] == "Ursaluna"
    assert rows[1]["team_id"] == "YV8VbSG82iS8rMz0hhwb"
    assert rows[1]["ability"] == ""
    assert rows[1]["moves"] == ""

    fallback_player_row = rows[2]
    assert fallback_player_row["pokemon_name"] == "Incineroar"
    assert fallback_player_row["record_wins"] == ""
    assert fallback_player_row["record_losses"] == ""


def test_extract_falls_back_to_synthetic_team_id_without_team_link(tmp_path):
    session = _session_for_one_tournament()
    output_path = tmp_path / "munchstats.csv"

    munchstats.extract(output_path, [TOURNAMENT_ID], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    fallback_row = next(row for row in rows if row["pokemon_name"] == "Incineroar")
    assert fallback_row["team_id"] == f"{TOURNAMENT_ID}:No Link Player"


def test_extract_derives_stable_player_id_from_name_and_country(tmp_path):
    session = _session_for_one_tournament()
    output_path = tmp_path / "munchstats.csv"

    munchstats.extract(output_path, [TOURNAMENT_ID], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    player_ids = {row["pokemon_name"]: row["player_id"] for row in rows}
    assert player_ids["Miraidon"] == player_ids["Ursaluna"]
    assert player_ids["Miraidon"] != player_ids["Incineroar"]


def test_extract_defaults_to_full_tournaments_index(tmp_path):
    session = _session_for_one_tournament()
    output_path = tmp_path / "munchstats.csv"

    munchstats.extract(output_path, session=session)

    assert munchstats.TOURNAMENTS_INDEX_URL in session.requested_urls
    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
