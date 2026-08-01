from pipelines import versioning


def test_latest_published_version_picks_highest_semver(tmp_path):
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    for name in ("manifest-0.1.0.json", "manifest-0.2.0.json", "manifest-0.10.0.json"):
        (manifests_dir / name).write_text("{}")

    assert versioning.latest_published_version(manifests_dir) == "0.10.0"


def test_latest_published_version_ignores_non_matching_files(tmp_path):
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()
    (manifests_dir / "manifest.template.json").write_text("{}")
    (manifests_dir / "README.md").write_text("")
    (manifests_dir / "manifest-1.2.3.json").write_text("{}")

    assert versioning.latest_published_version(manifests_dir) == "1.2.3"


def test_latest_published_version_defaults_when_no_manifests(tmp_path):
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir()

    assert (
        versioning.latest_published_version(manifests_dir) == versioning.UNRELEASED_DATASET_VERSION
    )


def test_latest_published_version_defaults_when_dir_missing(tmp_path):
    assert (
        versioning.latest_published_version(tmp_path / "does-not-exist")
        == versioning.UNRELEASED_DATASET_VERSION
    )
