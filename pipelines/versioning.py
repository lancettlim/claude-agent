"""Shared helper for discovering the latest published dataset_version.

Used as the default `dataset_version` stamped onto new staging snapshots
(pipelines/cli.py's `extract` subcommand) and onto validation reports
(pipelines/validate/report.py), so both default to "this run is staged
toward a refresh of the currently-published version" rather than a
hardcoded placeholder — see backlog.md #4. A release publishing a MINOR/
MAJOR bump instead of a PATCH refresh should pass an explicit
--dataset-version to override this.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTS_DIR = REPO_ROOT / "releases" / "manifests"

UNRELEASED_DATASET_VERSION = "0.0.0-dev"

_MANIFEST_VERSION_PATTERN = re.compile(r"^manifest-(\d+)\.(\d+)\.(\d+)\.json$")


def latest_published_version(manifests_dir: Path = MANIFESTS_DIR) -> str:
    """Return the highest MAJOR.MINOR.PATCH version with a published
    manifest under releases/manifests/, or UNRELEASED_DATASET_VERSION if
    none has ever been published (a fresh, pre-release repo)."""
    if not manifests_dir.exists():
        return UNRELEASED_DATASET_VERSION

    versions: list[tuple[int, int, int]] = []
    for path in manifests_dir.glob("manifest-*.json"):
        match = _MANIFEST_VERSION_PATTERN.match(path.name)
        if match:
            versions.append(tuple(int(part) for part in match.groups()))

    if not versions:
        return UNRELEASED_DATASET_VERSION
    major, minor, patch = max(versions)
    return f"{major}.{minor}.{patch}"
