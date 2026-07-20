"""Assemble a versioned release package under releases/, per
docs/dataset-spec.md's "Release package" section: one CSV per core entity
plus manifest.json and CHANGELOG.md.

Gated on reports/validation/validation_report.json: a release is refused
(ReleaseBlockedError) unless that report exists and reports zero
release_blocking_findings, per CLAUDE.md's "Don't ship ungated data" and
dataset-spec.md's "Any unmapped or low-confidence rows must be documented
in the manifest and excluded from release tables unless explicitly
approved." Run `pipelines.cli validate` (dbt build + report generation)
before publishing.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.validate.report import DUPLICATE_KEY_TABLES, REPORT_PATH

REPO_ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = REPO_ROOT / "data" / "normalized"
STAGING_DIR = REPO_ROOT / "data" / "staging"
RELEASES_DATA_DIR = REPO_ROOT / "releases" / "data"
MANIFESTS_DIR = REPO_ROOT / "releases" / "manifests"
CHANGELOGS_DIR = REPO_ROOT / "releases" / "changelogs"
DEFAULT_ASSET_CACHE_DIR = REPO_ROOT / "data" / "assets" / "bulbagarden"
IMAGES_SUBDIR = "images"

# table_name -> primary_key, reusing the table list report.py already
# maintains rather than duplicating it.
TABLES: dict[str, str] = {
    name: primary_key for name, (primary_key, _) in DUPLICATE_KEY_TABLES.items()
}

# source_name -> (source_url, staging_filename), matching
# releases/manifests/manifest.template.json's sources array.
SOURCES: dict[str, tuple[str, str]] = {
    "PokéAPI": ("https://github.com/PokeAPI/pokeapi", "pokeapi.csv"),
    "OP.GG Pokémon Champions": ("https://op.gg/pokemon-champions/pokedex", "opgg_champions.csv"),
    "MunchStats": ("https://github.com/PizzaTimeJoshua/munchstats", "munchstats.csv"),
    "PokéBase": ("https://pokebase.app/pokemon-champions/pokemon", "pokebase.csv"),
    "Bulbagarden Archives": ("https://archives.bulbagarden.net/w/api.php", "bulbagarden.csv"),
}

CHANGELOG_TEMPLATE = (REPO_ROOT / "releases" / "changelogs" / "CHANGELOG.template.md").read_text()


class ReleaseBlockedError(RuntimeError):
    """Raised when the validation report is missing or reports failing gates."""


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _load_validation_report(validation_report_path: Path) -> dict[str, Any]:
    if not validation_report_path.exists():
        raise ReleaseBlockedError(
            f"{validation_report_path} not found — run `pipelines.cli validate` "
            "(or `make validate`) before publishing a release"
        )
    report = json.loads(validation_report_path.read_text())
    findings = report["release_blocking_findings"]
    if findings:
        raise ReleaseBlockedError(f"Cannot publish release: gates failing: {findings}")
    return report


def _build_sources(staging_dir: Path) -> list[dict[str, Any]]:
    sources = []
    for source_name, (source_url, filename) in SOURCES.items():
        rows = _read_csv_rows(staging_dir / filename)
        sources.append(
            {
                "source_name": source_name,
                "source_url": source_url,
                "extracted_at_utc": rows[0]["extracted_at_utc"] if rows else None,
                "record_count": len(rows),
            }
        )
    return sources


def _copy_tables(normalized_dir: Path, dest_dir: Path) -> list[dict[str, Any]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    tables = []
    for table_name, primary_key in TABLES.items():
        src = normalized_dir / f"{table_name}.csv"
        dest = dest_dir / f"{table_name}.csv"
        shutil.copyfile(src, dest)
        tables.append(
            {
                "table_name": table_name,
                "file_name": dest.name,
                "primary_key": primary_key,
                "row_count": len(_read_csv_rows(dest)),
            }
        )
    return tables


def _copy_referenced_images(
    dest_dir: Path, *, asset_cache_dir: Path = DEFAULT_ASSET_CACHE_DIR
) -> dict[str, Any]:
    """Copy every file pokemon_asset.csv's local_cache_path column
    references from the local extractor cache into dest_dir/images/, so the
    release package is self-contained. dest_dir is the release's own
    per-version directory (releases_data_dir/<dataset_version>), and
    pokemon_asset.csv must already be present there (i.e. this runs after
    _copy_tables). Returns the manifest's "images" block."""
    pokemon_asset_rows = _read_csv_rows(dest_dir / "pokemon_asset.csv")
    images_dir = dest_dir / IMAGES_SUBDIR
    images_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for row in pokemon_asset_rows:
        local_cache_path = row["local_cache_path"]
        src = asset_cache_dir / local_cache_path
        dest = images_dir / local_cache_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        copied += 1
    return {"count": copied, "directory": f"{IMAGES_SUBDIR}/"}


def _build_quality_checks(validation_report: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for coverage_check in validation_report["coverage_checks"]:
        checks.append(
            {
                "check_name": coverage_check["check_name"],
                "status": coverage_check["status"],
                "metric_value": coverage_check["metric_value"],
                "threshold": coverage_check["threshold"],
            }
        )

    null_rate_checks = validation_report["null_rate_checks"]
    null_rate_values = [
        c["metric_value"] for c in null_rate_checks if c["metric_value"] is not None
    ]
    checks.append(
        {
            "check_name": "required_field_null_rate",
            "status": "pass" if all(c["status"] == "pass" for c in null_rate_checks) else "fail",
            "metric_value": max(null_rate_values) if null_rate_values else None,
            "threshold": "<=0.01",
        }
    )

    duplicate_checks = validation_report["duplicate_key_checks"]
    duplicate_counts = [
        c["duplicate_count"] for c in duplicate_checks if c["duplicate_count"] is not None
    ]
    checks.append(
        {
            "check_name": "duplicate_primary_key_violations",
            "status": "pass" if all(c["status"] == "pass" for c in duplicate_checks) else "fail",
            "metric_value": sum(duplicate_counts) if duplicate_counts else None,
            "threshold": "=0",
        }
    )

    referential_checks = validation_report["referential_integrity_checks"]
    violation_counts = [
        c["violation_count"] for c in referential_checks if c["violation_count"] is not None
    ]
    checks.append(
        {
            "check_name": "referential_integrity",
            "status": "pass" if all(c["status"] == "pass" for c in referential_checks) else "fail",
            "metric_value": sum(violation_counts) if violation_counts else None,
            "threshold": "all resolve",
        }
    )
    return checks


def _write_changelog(
    path: Path,
    *,
    dataset_version: str,
    published_at_utc: str,
    sources: list[dict[str, Any]],
    known_limitations: list[str],
) -> None:
    source_by_name = {s["source_name"]: s for s in sources}
    text = (
        CHANGELOG_TEMPLATE.replace("{VERSION}", dataset_version)
        .replace("{PUBLISHED_AT_UTC}", published_at_utc)
        .replace("{POKEAPI_EXTRACTED_AT_UTC}", str(source_by_name["PokéAPI"]["extracted_at_utc"]))
        .replace(
            "{OPGG_EXTRACTED_AT_UTC}",
            str(source_by_name["OP.GG Pokémon Champions"]["extracted_at_utc"]),
        )
        .replace(
            "{MUNCHSTATS_EXTRACTED_AT_UTC}", str(source_by_name["MunchStats"]["extracted_at_utc"])
        )
        .replace("{POKEBASE_EXTRACTED_AT_UTC}", str(source_by_name["PokéBase"]["extracted_at_utc"]))
        .replace(
            "{BULBAGARDEN_EXTRACTED_AT_UTC}",
            str(source_by_name["Bulbagarden Archives"]["extracted_at_utc"]),
        )
    )
    limitations_block = (
        "\n".join(f"- {item}" for item in known_limitations) if known_limitations else "- None"
    )
    text = text.replace(
        "### New\n\n- {describe any newly identified coverage gaps or low-confidence mappings}",
        f"### New\n\n{limitations_block}",
    )
    path.write_text(text)


def build(
    dataset_version: str,
    *,
    known_limitations: list[str] | None = None,
    validation_report_path: Path = REPORT_PATH,
    normalized_dir: Path = NORMALIZED_DIR,
    staging_dir: Path = STAGING_DIR,
    releases_data_dir: Path = RELEASES_DATA_DIR,
    manifests_dir: Path = MANIFESTS_DIR,
    changelogs_dir: Path = CHANGELOGS_DIR,
    asset_cache_dir: Path = DEFAULT_ASSET_CACHE_DIR,
) -> dict[str, Any]:
    """Build a versioned release package: copies data/normalized/*.csv to
    releases/data/<dataset_version>/, copies the sprite images
    pokemon_asset.csv references into releases/data/<dataset_version>/images/,
    and writes releases/manifests/manifest-<dataset_version>.json and
    releases/changelogs/CHANGELOG-<dataset_version>.md.

    Raises ReleaseBlockedError if reports/validation/validation_report.json
    is missing or reports any release_blocking_findings.
    """
    validation_report = _load_validation_report(validation_report_path)

    published_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sources = _build_sources(staging_dir)
    release_dir = releases_data_dir / dataset_version
    tables = _copy_tables(normalized_dir, release_dir)
    images = _copy_referenced_images(release_dir, asset_cache_dir=asset_cache_dir)
    quality_checks = _build_quality_checks(validation_report)

    manifest = {
        "dataset_version": dataset_version,
        "published_at_utc": published_at_utc,
        "sources": sources,
        "tables": tables,
        "images": images,
        "quality_checks": quality_checks,
        "known_limitations": known_limitations or [],
    }

    manifests_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifests_dir / f"manifest-{dataset_version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    changelogs_dir.mkdir(parents=True, exist_ok=True)
    changelog_path = changelogs_dir / f"CHANGELOG-{dataset_version}.md"
    _write_changelog(
        changelog_path,
        dataset_version=dataset_version,
        published_at_utc=published_at_utc,
        sources=sources,
        known_limitations=known_limitations or [],
    )

    return manifest
