import csv
import json

from pipelines.extract import summary
from pipelines.extract.http import RequestStats


def _write_schema(path, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fields": fields}), encoding="utf-8")


def _write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_required_fields_filters_to_required_true(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "STAGING_SCHEMA_DIR", tmp_path)
    _write_schema(
        tmp_path / "fake_source.schema.json",
        [
            {"name": "a", "required": True},
            {"name": "b", "required": False},
            {"name": "c", "required": True},
        ],
    )

    assert summary.required_fields("fake_source") == ["a", "c"]


def test_required_fields_empty_when_schema_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "STAGING_SCHEMA_DIR", tmp_path)

    assert summary.required_fields("no_such_source") == []


def test_rows_and_null_rate_counts_only_required_field_blanks(tmp_path):
    output_path = tmp_path / "data.csv"
    _write_csv(
        output_path,
        [
            {"a": "1", "b": ""},
            {"a": "", "b": ""},
        ],
        ["a", "b"],
    )

    rows_written, null_rate = summary.rows_and_required_field_null_rate(output_path, ["a"])

    assert rows_written == 2
    # 1 of 2 required-field cells (just column "a") is blank; "b" isn't
    # required, so its blanks don't count.
    assert null_rate == 0.5


def test_rows_and_null_rate_zero_when_no_required_fields(tmp_path):
    output_path = tmp_path / "data.csv"
    _write_csv(output_path, [{"a": ""}], ["a"])

    assert summary.rows_and_required_field_null_rate(output_path, []) == (0, 0.0)


def test_rows_and_null_rate_zero_when_output_missing(tmp_path):
    assert summary.rows_and_required_field_null_rate(tmp_path / "missing.csv", ["a"]) == (0, 0.0)


def _result(**overrides):
    defaults = dict(
        source_name="Fake Source",
        endpoint="https://example.test/fake",
        staging_subdir="fake_source",
        output_path=None,
        stats=RequestStats(),
        error=None,
    )
    defaults.update(overrides)
    return summary.SourceRunResult(**defaults)


def test_build_source_entry_all_requests_succeeded(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "STAGING_SCHEMA_DIR", tmp_path)
    _write_schema(tmp_path / "fake_source.schema.json", [{"name": "a", "required": True}])
    output_path = tmp_path / "fake_source.csv"
    _write_csv(output_path, [{"a": "1"}, {"a": "2"}], ["a"])
    stats = RequestStats(attempted=5, succeeded=5)

    entry = summary.build_source_entry(_result(output_path=output_path, stats=stats))

    assert entry["source_name"] == "Fake Source"
    assert entry["availability"] == "reachable, HTTP 200 for all requests"
    assert entry["requests_attempted"] == 5
    assert entry["requests_succeeded"] == 5
    assert entry["request_success_rate"] == 1.0
    assert entry["rows_written"] == 2


def test_build_source_entry_partial_failures(tmp_path):
    output_path = tmp_path / "fake_source.csv"
    _write_csv(output_path, [], ["a"])
    stats = RequestStats(attempted=4, succeeded=3, failed_urls=["https://example.test/bad"])

    entry = summary.build_source_entry(_result(output_path=output_path, stats=stats))

    assert entry["availability"] == "reachable, but 1/4 request(s) failed"
    assert entry["request_success_rate"] == 0.75


def test_build_source_entry_error_reports_unreachable(tmp_path):
    output_path = tmp_path / "fake_source.csv"
    stats = RequestStats(attempted=1, succeeded=0, failed_urls=["https://example.test/x"])

    entry = summary.build_source_entry(
        _result(output_path=output_path, stats=stats, error="ConnectionError: boom")
    )

    assert entry["availability"] == "unreachable: ConnectionError: boom"
    assert entry["rows_written"] == 0


def test_build_source_entry_no_requests_attempted(tmp_path):
    entry = summary.build_source_entry(_result(output_path=tmp_path / "missing.csv"))

    assert entry["availability"] == "no requests attempted"
    assert entry["request_success_rate"] is None


def test_merge_source_entry_replaces_only_matching_source():
    document = {
        "sources": [
            {"source_name": "A", "rows_written": 1},
            {"source_name": "B", "rows_written": 2},
        ]
    }

    updated = summary.merge_source_entry(document, {"source_name": "A", "rows_written": 99})

    by_name = {s["source_name"]: s for s in updated["sources"]}
    assert by_name["A"]["rows_written"] == 99
    assert by_name["B"]["rows_written"] == 2


def test_merge_source_entry_appends_new_source():
    document = {"sources": [{"source_name": "A", "rows_written": 1}]}

    updated = summary.merge_source_entry(document, {"source_name": "B", "rows_written": 2})

    assert {s["source_name"] for s in updated["sources"]} == {"A", "B"}


def test_load_document_defaults_when_missing(tmp_path):
    document = summary.load_document(tmp_path / "does-not-exist.json")

    assert document["sources"] == []
    assert document["description"] == summary.DESCRIPTION


def test_update_merges_and_preserves_other_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(summary, "STAGING_SCHEMA_DIR", tmp_path)
    _write_schema(tmp_path / "fake_source.schema.json", [{"name": "a", "required": True}])
    path = tmp_path / "extraction_summary.json"
    summary.write_document(
        {
            "description": summary.DESCRIPTION,
            "generated_at_utc": "2020-01-01T00:00:00Z",
            "dataset_version": "0.0.0",
            "sources": [{"source_name": "Other Source", "rows_written": 42}],
        },
        path,
    )
    output_path = tmp_path / "fake_source.csv"
    _write_csv(output_path, [{"a": "1"}], ["a"])
    stats = RequestStats(attempted=1, succeeded=1)

    document = summary.update(
        _result(output_path=output_path, stats=stats),
        dataset_version="1.2.3",
        path=path,
    )

    assert document["dataset_version"] == "1.2.3"
    by_name = {s["source_name"]: s for s in document["sources"]}
    assert by_name["Other Source"]["rows_written"] == 42
    assert by_name["Fake Source"]["rows_written"] == 1
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == document
