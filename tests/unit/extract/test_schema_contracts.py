"""Backlog #41: every extractor's FIELDNAMES must match the field list its
data/staging/<subdir>.schema.json contract declares -- name-for-name, in
the same order -- so a code change that adds/renames/drops a staging
column can't drift silently out of sync with the documented contract.
This is the staging half of schema-drift enforcement; see
tests/unit/validate/test_report.py for the normalized-layer half (checked
against a real dbt build's CSV output, not just the extractor code)."""

from pathlib import Path

import pytest

from pipelines.cli import _EXTRACTORS
from pipelines.extract import pokeapi
from pipelines.schema_contracts import schema_field_names

REPO_ROOT = Path(__file__).resolve().parents[3]
STAGING_SCHEMA_DIR = REPO_ROOT / "data" / "staging"

# Derived from pipelines/cli.py's _EXTRACTORS (source -> staging
# subdirectory) rather than restated here: a hand-maintained copy silently
# stops covering any extractor added after it was last edited, which is the
# same failure mode backlog #37 removed from the validation report.
_EXTRACTOR_SCHEMAS = [(module, subdir) for module, subdir in _EXTRACTORS.values()]


@pytest.mark.parametrize(
    "module,schema_stem", _EXTRACTOR_SCHEMAS, ids=[stem for _, stem in _EXTRACTOR_SCHEMAS]
)
def test_extractor_fieldnames_match_schema_contract(module, schema_stem):
    schema_path = STAGING_SCHEMA_DIR / f"{schema_stem}.schema.json"

    assert module.FIELDNAMES == schema_field_names(schema_path)


@pytest.mark.parametrize(
    "module_fieldnames,schema_stem",
    [
        (pokeapi.MOVE_FIELDNAMES, "pokeapi_move"),
        (pokeapi.ABILITY_FIELDNAMES, "pokeapi_ability"),
        (pokeapi.ITEM_FIELDNAMES, "pokeapi_item"),
    ],
    ids=["pokeapi_move", "pokeapi_ability", "pokeapi_item"],
)
def test_pokeapi_detail_fieldnames_match_schema_contract(module_fieldnames, schema_stem):
    schema_path = STAGING_SCHEMA_DIR / f"{schema_stem}.schema.json"

    assert module_fieldnames == schema_field_names(schema_path)
