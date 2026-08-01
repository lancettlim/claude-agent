import csv
import os
import subprocess
import time

from pipelines import cli


def _write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_dated_snapshot_path_is_source_subdir_slash_date(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)

    path = cli._dated_snapshot_path("pokeapi", "2026-07-30")

    assert path == tmp_path / "pokeapi" / "2026-07-30.csv"


def test_latest_snapshot_path_picks_most_recent_date(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    source_dir = tmp_path / "munchstats"
    for date_str in ("2026-07-01", "2026-07-15", "2026-07-08"):
        _write_csv(source_dir / f"{date_str}.csv", [], ["a"])

    assert cli._latest_snapshot_path("munchstats") == source_dir / "2026-07-15.csv"


def test_latest_snapshot_path_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)

    assert cli._latest_snapshot_path("munchstats") is None


def test_prune_old_snapshots_keeps_only_the_newest(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    source_dir = tmp_path / "bulbagarden"
    dates = [f"2026-01-{day:02d}" for day in range(1, 13)]  # 12 snapshots
    for date_str in dates:
        _write_csv(source_dir / f"{date_str}.csv", [], ["a"])

    cli._prune_old_snapshots("bulbagarden")  # retention count is 10

    remaining = sorted(p.stem for p in source_dir.glob("*.csv"))
    assert remaining == dates[-10:]


def test_prune_old_snapshots_no_op_under_retention(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    source_dir = tmp_path / "pokebase"
    _write_csv(source_dir / "2026-07-30.csv", [], ["a"])

    cli._prune_old_snapshots("pokebase")

    assert [p.name for p in source_dir.glob("*.csv")] == ["2026-07-30.csv"]


def test_referenced_move_ability_item_names_reads_latest_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    fieldnames = ["ability", "item_name", "moves"]
    _write_csv(
        tmp_path / "munchstats" / "2026-07-01.csv",
        [{"ability": "Stale Ability", "item_name": "Stale Item", "moves": "Stale Move"}],
        fieldnames,
    )
    _write_csv(
        tmp_path / "munchstats" / "2026-07-15.csv",
        [{"ability": "Intimidate", "item_name": "Choice Band", "moves": "Flare Blitz|Earthquake"}],
        fieldnames,
    )

    moves, abilities, items = cli._referenced_move_ability_item_names()

    assert moves == {"Flare Blitz", "Earthquake"}
    assert abilities == {"Intimidate"}
    assert items == {"Choice Band"}


def test_referenced_move_ability_item_names_empty_when_no_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)

    assert cli._referenced_move_ability_item_names() == (set(), set(), set())


class _RecordingExtractor:
    def __init__(self):
        self.calls = []

    def extract(self, output_path, *, dataset_version=None, session=None):
        self.calls.append((output_path, dataset_version))
        _write_csv(output_path, [], ["a"])


def test_run_extract_writes_dated_snapshot_and_prunes(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    fake = _RecordingExtractor()
    monkeypatch.setattr(cli, "_EXTRACTORS", {"fake": (fake, "fake_source")})
    monkeypatch.setattr(cli, "_RETENTION_COUNTS", {"fake_source": 2})
    monkeypatch.setattr(cli, "_snapshot_date", lambda: "2026-07-30")

    exit_code = cli._run_extract("fake", "1.2.3")

    assert exit_code == 0
    assert fake.calls == [(tmp_path / "fake_source" / "2026-07-30.csv", "1.2.3")]
    assert (tmp_path / "fake_source" / "2026-07-30.csv").exists()


def test_run_extract_all_runs_every_source_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "STAGING_DIR", tmp_path)
    call_order = []

    class _Recorder:
        def __init__(self, name):
            self._name = name

        def extract(self, output_path, *, dataset_version=None, session=None):
            call_order.append(self._name)
            _write_csv(output_path, [], ["a"])

    monkeypatch.setattr(
        cli,
        "_EXTRACTORS",
        {
            "first": (_Recorder("first"), "first_dir"),
            "second": (_Recorder("second"), "second_dir"),
        },
    )
    monkeypatch.setattr(cli, "_RETENTION_COUNTS", {"first_dir": 5, "second_dir": 5})

    exit_code = cli._run_extract("all", "1.2.3")

    assert exit_code == 0
    assert call_order == ["first", "second"]


def test_main_extract_defaults_dataset_version_to_latest_published(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli.versioning, "latest_published_version", lambda: "0.9.9")
    monkeypatch.setattr(
        cli,
        "_run_extract",
        lambda source, dataset_version: (
            captured.update(source=source, dataset_version=dataset_version) or 0
        ),
    )

    exit_code = cli.main(["extract", "pokeapi"])

    assert exit_code == 0
    assert captured == {"source": "pokeapi", "dataset_version": "0.9.9"}


def test_main_extract_dataset_version_override(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        cli,
        "_run_extract",
        lambda source, dataset_version: (
            captured.update(source=source, dataset_version=dataset_version) or 0
        ),
    )

    exit_code = cli.main(["extract", "opgg", "--dataset-version", "9.9.9"])

    assert exit_code == 0
    assert captured == {"source": "opgg", "dataset_version": "9.9.9"}


def _run_results_path(dbt_project_dir):
    return dbt_project_dir / "target" / "run_results.json"


def test_run_validate_passes_when_gates_clean(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DBT_PROJECT_DIR", tmp_path)

    def fake_run(cmd, cwd):
        _run_results_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        _run_results_path(tmp_path).write_text("{}")
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.report, "generate", lambda: {"release_blocking_findings": []})

    assert cli._run_validate() == 0


def test_run_validate_fails_when_gates_report_findings(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DBT_PROJECT_DIR", tmp_path)

    def fake_run(cmd, cwd):
        _run_results_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        _run_results_path(tmp_path).write_text("{}")
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(
        cli.report, "generate", lambda: {"release_blocking_findings": ["pokemon: status=fail"]}
    )

    assert cli._run_validate() == 1


def test_run_validate_propagates_unexpected_dbt_crash_code(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DBT_PROJECT_DIR", tmp_path)
    calls = []

    def fake_run(cmd, cwd):
        return subprocess.CompletedProcess(cmd, returncode=2)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.report, "generate", lambda: calls.append("called"))

    assert cli._run_validate() == 2
    assert calls == []


def test_run_validate_refuses_stale_run_results_after_compile_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DBT_PROJECT_DIR", tmp_path)
    stale_path = _run_results_path(tmp_path)
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text("{}")
    # Back-date the stale artifact so it predates _run_validate's start time,
    # simulating a compile/connection error that exits 1 without rewriting it.
    old_time = time.time() - 3600
    os.utime(stale_path, (old_time, old_time))
    calls = []

    def fake_run(cmd, cwd):
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.report, "generate", lambda: calls.append("called"))

    assert cli._run_validate() == 1
    assert calls == []


def test_main_extract_accepts_all_choice(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        cli, "_run_extract", lambda source, dataset_version: captured.update(source=source) or 0
    )

    exit_code = cli.main(["extract", "all", "--dataset-version", "1.0.0"])

    assert exit_code == 0
    assert captured == {"source": "all"}
