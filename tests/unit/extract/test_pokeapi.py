import csv

from pipelines.extract import pokeapi


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(
        self, payloads_by_name: dict[str, dict], list_names: list[str] | None = None
    ) -> None:
        self._payloads_by_name = payloads_by_name
        self._list_names = list_names
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        if url.startswith(f"{pokeapi.API_BASE_URL}/pokemon?"):
            return _FakeResponse({"results": [{"name": name} for name in self._list_names]})
        name = url.rstrip("/").rsplit("/", 1)[-1]
        return _FakeResponse(self._payloads_by_name[name])


def _payload(
    resource_id: int, name: str, stats: dict[str, int], *, species_name: str, species_id: int
) -> dict:
    return {
        "id": resource_id,
        "name": name,
        "species": {
            "name": species_name,
            "url": f"https://pokeapi.co/api/v2/pokemon-species/{species_id}/",
        },
        "stats": [
            {"base_stat": value, "stat": {"name": stat_name}} for stat_name, value in stats.items()
        ],
    }


def test_extract_writes_rows_with_stats_and_provenance(tmp_path):
    payloads = {
        "bulbasaur": _payload(
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
            species_name="bulbasaur",
            species_id=1,
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, ["bulbasaur"], dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert session.requested_urls == ["https://pokeapi.co/api/v2/pokemon/bulbasaur"]
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
    assert row["source_url"] == "https://pokeapi.co/api/v2/pokemon/bulbasaur"
    assert row["source_record_id"] == "1"
    assert row["dataset_version"] == "0.1.0"
    assert row["extracted_at_utc"]


def test_extract_uses_species_id_and_name_for_alt_forms(tmp_path):
    payloads = {
        "charizard-mega-x": _payload(
            10034,
            "charizard-mega-x",
            {
                "hp": 78,
                "attack": 130,
                "defense": 111,
                "special-attack": 130,
                "special-defense": 85,
                "speed": 100,
            },
            species_name="charizard",
            species_id=6,
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, ["charizard-mega-x"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["pokemon_id"] == "6"
    assert row["pokemon_name"] == "charizard"
    assert row["form_name"] == "charizard-mega-x"
    assert row["source_record_id"] == "10034"


def test_extract_preserves_requested_identifier_order(tmp_path):
    payloads = {
        "charmander": _payload(
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
            species_name="charmander",
            species_id=4,
        ),
        "squirtle": _payload(
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
            species_name="squirtle",
            species_id=7,
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, ["squirtle", "charmander"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert [row["pokemon_name"] for row in rows] == ["squirtle", "charmander"]


def test_extract_defaults_to_fetching_full_pokemon_list(tmp_path):
    payloads = {
        "bulbasaur": _payload(
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
            species_name="bulbasaur",
            species_id=1,
        )
    }
    session = _FakeSession(payloads, list_names=["bulbasaur"])
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, session=session)

    assert session.requested_urls[0].startswith(f"{pokeapi.API_BASE_URL}/pokemon?")
    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["pokemon_name"] == "bulbasaur"


def test_extract_defaults_dataset_version_when_not_provided(tmp_path):
    payloads = {
        "bulbasaur": _payload(
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
            species_name="bulbasaur",
            species_id=1,
        )
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, ["bulbasaur"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["dataset_version"] == pokeapi.DEFAULT_DATASET_VERSION
