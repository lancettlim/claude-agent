import csv
import json

import pytest

from pipelines.render import data_source


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _populate_normalized(tmp_path):
    normalized_dir = tmp_path / "normalized"
    _write_csv(
        normalized_dir / "tournament_team.csv",
        [{"team_id": "team-1", "player_id": "p1", "placement": "3"}],
    )
    _write_csv(
        normalized_dir / "tournament_team_member.csv",
        [
            {
                "team_id": "team-1",
                "pokemon_key": "incineroar",
                "slot_number": "2",
                "item_name": "Sitrus Berry",
                "ability": "Intimidate",
                "tera_type": "Ghost",
                "moves": "Fake Out|Flare Blitz",
            },
            {
                "team_id": "team-1",
                "pokemon_key": "venusaur",
                "slot_number": "1",
                "item_name": "",
                "ability": "Chlorophyll",
                "tera_type": "",
                "moves": "Giga Drain",
            },
        ],
    )
    _write_csv(
        normalized_dir / "pokemon.csv",
        [
            {
                "pokemon_key": "incineroar",
                "pokemon_id": "727",
                "pokemon_name": "Incineroar",
                "form_name": "incineroar",
            },
            {
                "pokemon_key": "venusaur",
                "pokemon_id": "3",
                "pokemon_name": "Venusaur",
                "form_name": "venusaur",
            },
        ],
    )
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "incineroar", "local_cache_path": "0727.png"}],
    )
    asset_cache_dir = tmp_path / "assets" / "bulbagarden"
    asset_cache_dir.mkdir(parents=True)
    (asset_cache_dir / "0727.png").write_bytes(b"fake-sprite-bytes")
    return normalized_dir, asset_cache_dir


def test_load_from_team_id_sorts_by_slot_and_resolves_sprite(tmp_path):
    normalized_dir, asset_cache_dir = _populate_normalized(tmp_path)

    card = data_source.load_from_team_id(
        "team-1", normalized_dir=normalized_dir, asset_cache_dir=asset_cache_dir
    )

    assert card.team_name == "team-1"
    assert card.subtitle == "p1 · 3"
    assert [s.slot_number for s in card.slots] == [1, 2]

    venusaur_slot = card.slots[0]
    assert venusaur_slot.pokemon_name == "Venusaur"
    assert venusaur_slot.moves == ["Giga Drain"]
    assert venusaur_slot.item_name is None
    assert venusaur_slot.sprite_path is None  # not in pokemon_asset.csv fixture

    incineroar_slot = card.slots[1]
    assert incineroar_slot.pokemon_name == "Incineroar"
    assert incineroar_slot.item_name == "Sitrus Berry"
    assert incineroar_slot.tera_type == "Ghost"
    assert incineroar_slot.moves == ["Fake Out", "Flare Blitz"]
    assert incineroar_slot.sprite_path == asset_cache_dir / "0727.png"


def test_load_from_team_id_raises_for_unknown_team(tmp_path):
    normalized_dir, asset_cache_dir = _populate_normalized(tmp_path)

    with pytest.raises(data_source.TeamNotFoundError):
        data_source.load_from_team_id(
            "no-such-team", normalized_dir=normalized_dir, asset_cache_dir=asset_cache_dir
        )


def test_load_from_spec_resolves_against_ingested_dataset(tmp_path):
    normalized_dir, asset_cache_dir = _populate_normalized(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "team_name": "Ad-hoc Team",
                "subtitle": "recreated from a broadcast graphic",
                "slots": [
                    {
                        "pokemon_name": "Incineroar",
                        "form_name": "incineroar",
                        "item_name": "Sitrus Berry",
                        "ability": "Intimidate",
                        "nature": "Impish",
                        "moves": ["Fake Out", "Flare Blitz"],
                    }
                ],
            }
        )
    )

    card = data_source.load_from_spec(
        spec_path, normalized_dir=normalized_dir, asset_cache_dir=asset_cache_dir
    )

    assert card.team_name == "Ad-hoc Team"
    assert len(card.slots) == 1
    slot = card.slots[0]
    assert slot.pokemon_name == "Incineroar"
    assert slot.nature == "Impish"
    assert slot.sprite_path == asset_cache_dir / "0727.png"


def test_load_from_spec_degrades_gracefully_for_uningested_pokemon(tmp_path):
    normalized_dir, asset_cache_dir = _populate_normalized(tmp_path)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "team_name": "Unknown Team",
                "slots": [
                    {
                        "pokemon_name": "Miraidon",
                        "form_name": "miraidon",
                        "moves": ["Electro Drift"],
                    }
                ],
            }
        )
    )

    card = data_source.load_from_spec(
        spec_path, normalized_dir=normalized_dir, asset_cache_dir=asset_cache_dir
    )

    slot = card.slots[0]
    assert slot.pokemon_name == "Miraidon"
    assert slot.sprite_path is None


def test_load_move_types_reads_real_seed():
    move_types = data_source.load_move_types()
    assert move_types["ice punch"] == "ice"
    assert move_types["wave crash"] == "water"
