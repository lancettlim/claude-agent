import csv

import requests

from pipelines.extract import pokeapi


class _FakeResponse:
    def __init__(self, payload, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(
        self,
        payloads_by_name: dict[str, dict],
        list_names: list[str] | None = None,
        missing_names: set[str] | None = None,
        flaky_names: dict[str, int] | None = None,
    ) -> None:
        self._payloads_by_name = payloads_by_name
        self._list_names = list_names
        self._missing_names = missing_names or set()
        self._flaky_names = dict(flaky_names or {})
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int):
        self.requested_urls.append(url)
        if url.startswith(f"{pokeapi.API_BASE_URL}/pokemon?"):
            return _FakeResponse({"results": [{"name": name} for name in self._list_names]})
        name = url.rstrip("/").rsplit("/", 1)[-1]
        if name in self._missing_names:
            return _FakeResponse(None, status_code=404)
        remaining_failures = self._flaky_names.get(name, 0)
        if remaining_failures > 0:
            self._flaky_names[name] = remaining_failures - 1
            return _FakeResponse(None, status_code=500)
        return _FakeResponse(self._payloads_by_name[name])


def _payload(
    resource_id: int,
    name: str,
    stats: dict[str, int],
    *,
    species_name: str,
    species_id: int,
    types: list[str] | None = None,
) -> dict:
    types = types if types is not None else ["normal"]
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
        "types": [
            {"slot": slot, "type": {"name": type_name}} for slot, type_name in enumerate(types, 1)
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
            types=["grass", "poison"],
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
    assert row["type_1"] == "grass"
    assert row["type_2"] == "poison"
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


def test_extract_writes_null_type_2_for_single_type_pokemon(tmp_path):
    payloads = {
        "pikachu": _payload(
            25,
            "pikachu",
            {
                "hp": 35,
                "attack": 55,
                "defense": 40,
                "special-attack": 50,
                "special-defense": 50,
                "speed": 90,
            },
            species_name="pikachu",
            species_id=25,
            types=["electric"],
        ),
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi.csv"

    pokeapi.extract(output_path, ["pikachu"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["type_1"] == "electric"
    assert row["type_2"] == ""


def _move_payload(move_id: int, name: str, **overrides) -> dict:
    payload = {
        "id": move_id,
        "type": {"name": "electric"},
        "power": 90,
        "accuracy": 100,
        "damage_class": {"name": "special"},
        "priority": 0,
        "pp": 15,
        "effect_entries": [
            {"language": {"name": "en"}, "short_effect": "Has a 10% chance to paralyze."}
        ],
    }
    payload.update(overrides)
    return payload


def test_extract_moves_writes_move_detail_rows(tmp_path):
    payloads = {"thunderbolt": _move_payload(85, "thunderbolt")}
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["Thunderbolt"], dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert session.requested_urls == ["https://pokeapi.co/api/v2/move/thunderbolt"]
    assert len(rows) == 1
    row = rows[0]
    assert row["move_name"] == "Thunderbolt"
    assert row["move_type"] == "electric"
    assert row["power"] == "90"
    assert row["accuracy"] == "100"
    assert row["category"] == "special"
    assert row["priority"] == "0"
    assert row["pp"] == "15"
    assert row["short_effect"] == "Has a 10% chance to paralyze."
    assert row["source_name"] == "PokéAPI"
    assert row["source_record_id"] == "85"
    assert row["dataset_version"] == "0.1.0"


def test_extract_moves_slugifies_multi_word_names(tmp_path):
    payloads = {"ice-punch": _move_payload(8, "ice-punch", type={"name": "ice"})}
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["Ice Punch"], session=session)

    assert session.requested_urls == ["https://pokeapi.co/api/v2/move/ice-punch"]


def test_extract_moves_slugifies_curly_apostrophe_like_straight_one(tmp_path):
    # Real roster text sometimes uses a Unicode curly apostrophe ('King’s
    # Shield') instead of a straight one ('King's Rock') — both must
    # resolve to the same PokéAPI slug PokéAPI itself uses (no apostrophe
    # at all), or the curly form 400s as an unrecognized percent-encoded
    # byte sequence.
    payloads = {"kings-shield": _move_payload(367, "kings-shield")}
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["King’s Shield"], session=session)

    assert session.requested_urls == ["https://pokeapi.co/api/v2/move/kings-shield"]
    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1


def test_extract_abilities_writes_ability_detail_rows(tmp_path):
    payloads = {
        "intimidate": {
            "id": 22,
            "effect_entries": [
                {
                    "language": {"name": "en"},
                    "short_effect": "Lowers the foes' Attack stat by one stage on switch-in.",
                }
            ],
        }
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_ability.csv"

    pokeapi.extract_abilities(
        output_path, ["Intimidate"], dataset_version="0.1.0", session=session
    )

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert session.requested_urls == ["https://pokeapi.co/api/v2/ability/intimidate"]
    assert row["ability_name"] == "Intimidate"
    assert row["short_effect"] == "Lowers the foes' Attack stat by one stage on switch-in."
    assert row["source_record_id"] == "22"
    assert row["dataset_version"] == "0.1.0"


def test_extract_items_writes_item_detail_rows(tmp_path):
    payloads = {
        "choice-band": {
            "id": 220,
            "effect_entries": [
                {
                    "language": {"name": "en"},
                    "short_effect": "Boosts Attack by 50%, but restricts the holder to one move.",
                }
            ],
        }
    }
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_item.csv"

    pokeapi.extract_items(output_path, ["Choice Band"], dataset_version="0.1.0", session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert session.requested_urls == ["https://pokeapi.co/api/v2/item/choice-band"]
    assert row["item_name"] == "Choice Band"
    assert row["short_effect"] == "Boosts Attack by 50%, but restricts the holder to one move."
    assert row["source_record_id"] == "220"
    assert row["dataset_version"] == "0.1.0"


def test_extract_moves_handles_no_english_effect_entry(tmp_path):
    payloads = {"splash": _move_payload(150, "splash", effect_entries=[])}
    session = _FakeSession(payloads)
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["Splash"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        row = next(csv.DictReader(fh))

    assert row["short_effect"] == ""


def test_extract_moves_skips_unresolvable_move_name(tmp_path):
    # Real tournament roster text can contain a genuinely malformed name
    # (e.g. a truncated "After Yo" instead of "After You") that 404s
    # against PokéAPI — this must be skipped, not crash the whole extract.
    payloads = {"thunderbolt": _move_payload(85, "thunderbolt")}
    session = _FakeSession(payloads, missing_names={"after-yo"})
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["After Yo", "Thunderbolt"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["move_name"] == "Thunderbolt"


def test_extract_abilities_skips_unresolvable_ability_name(tmp_path):
    payloads = {
        "intimidate": {
            "id": 22,
            "effect_entries": [{"language": {"name": "en"}, "short_effect": "Lowers Attack."}],
        }
    }
    session = _FakeSession(payloads, missing_names={"not-a-real-ability"})
    output_path = tmp_path / "pokeapi_ability.csv"

    pokeapi.extract_abilities(
        output_path, ["Not A Real Ability", "Intimidate"], session=session
    )

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["ability_name"] == "Intimidate"


def test_extract_moves_retries_transient_error_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(pokeapi.time, "sleep", lambda seconds: None)
    payloads = {"thunderbolt": _move_payload(85, "thunderbolt")}
    session = _FakeSession(payloads, flaky_names={"thunderbolt": 2})
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["Thunderbolt"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["move_name"] == "Thunderbolt"


def test_extract_moves_gives_up_after_persistent_transient_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pokeapi.time, "sleep", lambda seconds: None)
    payloads = {"thunderbolt": _move_payload(85, "thunderbolt")}
    # Always fails (more failures than retry attempts) — should be skipped,
    # not crash the whole extraction.
    session = _FakeSession(payloads, flaky_names={"thunderbolt": 99})
    output_path = tmp_path / "pokeapi_move.csv"

    pokeapi.extract_moves(output_path, ["Thunderbolt"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert rows == []


def test_extract_items_skips_unresolvable_item_name(tmp_path):
    payloads = {
        "choice-band": {
            "id": 220,
            "effect_entries": [{"language": {"name": "en"}, "short_effect": "Boosts Attack."}],
        }
    }
    session = _FakeSession(payloads, missing_names={"not-a-real-item"})
    output_path = tmp_path / "pokeapi_item.csv"

    pokeapi.extract_items(output_path, ["Not A Real Item", "Choice Band"], session=session)

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["item_name"] == "Choice Band"
