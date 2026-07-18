import csv
import json

from pipelines.extract import opgg


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, html: str) -> None:
        self._html = html
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        return _FakeResponse(self._html)


POKEMON_PAYLOADS = [
    {
        "id": 3,
        "key": "venusaur",
        "name": "Venusaur",
        "generation": 1,
        "stats": {
            "hp": 80,
            "attack": 82,
            "defense": 83,
            "spAttack": 100,
            "spDefense": 100,
            "speed": 80,
        },
    },
    {
        "id": 10033,
        "key": "mega-venusaur",
        "name": "Mega Venusaur",
        "generation": 1,
        "base_key": "venusaur",
        "item": "venusaurite",
        "stats": {
            "hp": 80,
            "attack": 100,
            "defense": 123,
            "spAttack": 122,
            "spDefense": 120,
            "speed": 80,
        },
    },
]


def _html_with_flight_payload(pokemon_payloads: list[dict]) -> str:
    """Build a synthetic page matching OP.GG's real structure: the Pokédex
    dataset embedded as a JSON-string-escaped array inside a Next.js Flight
    `self.__next_f.push(...)` script chunk."""
    inner_json = json.dumps(
        {"pokemon": pokemon_payloads, "types": ["grass"]}, separators=(",", ":")
    )
    escaped_inner_json = json.dumps(inner_json)
    return (
        "<html><body>"
        f'<script>self.__next_f.push([1,"8:{escaped_inner_json[1:-1]}"])</script>'
        "</body></html>"
    )


def test_extract_writes_rows_with_stats_and_provenance(tmp_path):
    session = _FakeSession(_html_with_flight_payload(POKEMON_PAYLOADS))
    output_path = tmp_path / "opgg_champions.csv"

    opgg.extract(output_path, dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert session.requested_urls == [opgg.PAGE_URL]
    assert len(rows) == 2

    row = rows[0]
    assert row["pokemon_id"] == "3"
    assert row["pokemon_name"] == "Venusaur"
    assert row["form_name"] == "Venusaur"
    assert row["is_legal"] == "True"
    assert row["hp"] == "80"
    assert row["attack"] == "82"
    assert row["defense"] == "83"
    assert row["sp_attack"] == "100"
    assert row["sp_defense"] == "100"
    assert row["speed"] == "80"
    assert row["stat_total"] == "525"
    assert row["regulation_code"] == ""
    assert row["source_name"] == "OP.GG Pokémon Champions"
    assert row["source_url"] == f"{opgg.PAGE_URL}/venusaur"
    assert row["source_record_id"] == "venusaur"
    assert row["dataset_version"] == "0.1.0"
    assert row["extracted_at_utc"]


def test_extract_nulls_pokemon_id_for_fabricated_form_ids(tmp_path):
    session = _FakeSession(_html_with_flight_payload(POKEMON_PAYLOADS))
    output_path = tmp_path / "opgg_champions.csv"

    opgg.extract(output_path, session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    mega_row = next(row for row in rows if row["source_record_id"] == "mega-venusaur")
    assert mega_row["pokemon_id"] == ""
    assert mega_row["pokemon_name"] == "Venusaur"
    assert mega_row["form_name"] == "Mega Venusaur"
    assert mega_row["stat_total"] == "625"


def test_extract_defaults_dataset_version_when_not_provided(tmp_path):
    session = _FakeSession(_html_with_flight_payload(POKEMON_PAYLOADS))
    output_path = tmp_path / "opgg_champions.csv"

    opgg.extract(output_path, session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["dataset_version"] == opgg.DEFAULT_DATASET_VERSION
