import csv

from pipelines.extract import pokeapi


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payloads_by_id: dict[int, dict]) -> None:
        self._payloads_by_id = payloads_by_id
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        pokemon_id = int(url.rstrip("/").rsplit("/", 1)[-1])
        return _FakeResponse(self._payloads_by_id[pokemon_id])


def _payload(pokemon_id: int, name: str, stats: dict[str, int]) -> dict:
    return {
        "id": pokemon_id,
        "name": name,
        "stats": [
            {"base_stat": value, "stat": {"name": stat_name}} for stat_name, value in stats.items()
        ],
    }


def test_extract_writes_rows_with_stats_and_provenance(tmp_path):
    payloads = {
        1: _payload(
            1,
            "bulbasaur",
            {
                "hp": 45,
                "attack": 49,
                "defense": 49,
                "special-attack": 65,
                "special-defense": 65,
                "speed": 45,
            },
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, [1], dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert session.requested_urls == ["https://pokeapi.co/api/v2/pokemon/1"]
    assert len(rows) == 1
    row = rows[0]
    assert row["pokemon_id"] == "1"
    assert row["pokemon_name"] == "bulbasaur"
    assert row["form_name"] == "bulbasaur"
    assert row["hp"] == "45"
    assert row["attack"] == "49"
    assert row["defense"] == "49"
    assert row["sp_attack"] == "65"
    assert row["sp_defense"] == "65"
    assert row["speed"] == "45"
    assert row["stat_total"] == "318"
    assert row["source_name"] == "PokéAPI"
    assert row["source_url"] == "https://pokeapi.co/api/v2/pokemon/1"
    assert row["source_record_id"] == "1"
    assert row["dataset_version"] == "0.1.0"
    assert row["extracted_at_utc"]


def test_extract_preserves_requested_id_order(tmp_path):
    payloads = {
        4: _payload(
            4,
            "charmander",
            {
                "hp": 39,
                "attack": 52,
                "defense": 43,
                "special-attack": 60,
                "special-defense": 50,
                "speed": 65,
            },
        ),
        7: _payload(
            7,
            "squirtle",
            {
                "hp": 44,
                "attack": 48,
                "defense": 65,
                "special-attack": 50,
                "special-defense": 64,
                "speed": 43,
            },
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, [7, 4], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert [row["pokemon_name"] for row in rows] == ["squirtle", "charmander"]


def test_extract_defaults_dataset_version_when_not_provided(tmp_path):
    payloads = {
        1: _payload(
            1,
            "bulbasaur",
            {
                "hp": 45,
                "attack": 49,
                "defense": 49,
                "special-attack": 65,
                "special-defense": 65,
                "speed": 45,
            },
        )
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, [1], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["dataset_version"] == pokeapi.DEFAULT_DATASET_VERSION
