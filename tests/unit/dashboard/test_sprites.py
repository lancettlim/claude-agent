import csv

from pipelines.dashboard import sprites


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_asset_map_returns_empty_dict_when_file_missing(tmp_path):
    assert sprites.load_asset_map(tmp_path) == {}


def test_load_asset_map(tmp_path):
    _write_csv(
        tmp_path / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "local_cache_path": "0025.png"}],
    )
    assert sprites.load_asset_map(tmp_path) == {"pikachu": "0025.png"}


def test_copy_sprites_copies_resolvable_keys(tmp_path):
    normalized_dir = tmp_path / "normalized"
    asset_cache_dir = tmp_path / "asset_cache"
    output_dir = tmp_path / "out"
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "local_cache_path": "0025.png"}],
    )
    source_path = asset_cache_dir / "0025.png"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(b"sprite-bytes")

    resolved = sprites.copy_sprites(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=asset_cache_dir,
    )

    assert resolved == {"pikachu": "images/pikachu.png"}
    assert (output_dir / "images" / "pikachu.png").read_bytes() == b"sprite-bytes"


def test_copy_sprites_skips_key_with_no_asset_row(tmp_path):
    output_dir = tmp_path / "out"
    resolved = sprites.copy_sprites(
        {"missingno"}, output_dir=output_dir, normalized_dir=tmp_path, asset_cache_dir=tmp_path
    )
    assert resolved == {}
    assert (output_dir / "images").exists()


def test_copy_sprites_skips_key_with_missing_source_file(tmp_path):
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "local_cache_path": "0025.png"}],
    )
    # asset_cache_dir intentionally has no 0025.png on disk.
    resolved = sprites.copy_sprites(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=tmp_path / "empty_cache",
    )
    assert resolved == {}


def test_copy_sprites_clears_stale_files_across_rebuilds(tmp_path):
    normalized_dir = tmp_path / "normalized"
    asset_cache_dir = tmp_path / "asset_cache"
    output_dir = tmp_path / "out"
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [
            {"pokemon_key": "pikachu", "local_cache_path": "0025.png"},
            {"pokemon_key": "raichu", "local_cache_path": "0026.png"},
        ],
    )
    for name in ("0025.png", "0026.png"):
        (asset_cache_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (asset_cache_dir / name).write_bytes(b"bytes")

    first = sprites.copy_sprites(
        {"pikachu", "raichu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=asset_cache_dir,
    )
    assert set(first) == {"pikachu", "raichu"}

    # A rebuild that only references pikachu should drop raichu.png rather
    # than leaving it behind as a stale file.
    second = sprites.copy_sprites(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=asset_cache_dir,
    )
    assert set(second) == {"pikachu"}
    assert not (output_dir / "images" / "raichu.png").exists()
    assert (output_dir / "images" / "pikachu.png").exists()


def test_copy_sprites_does_not_clobber_sibling_asset_subdirectories(tmp_path):
    """backlog.md #47: copy_sprites used to rmtree the whole images/
    directory, which would wipe out images/icons/ or
    images/reference_teams/ if this ran after those steps instead of
    before. It now prunes only its own top-level *.png files, so unrelated
    subdirectories survive regardless of call order."""
    normalized_dir = tmp_path / "normalized"
    asset_cache_dir = tmp_path / "asset_cache"
    output_dir = tmp_path / "out"
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "local_cache_path": "0025.png"}],
    )
    (asset_cache_dir / "0025.png").parent.mkdir(parents=True, exist_ok=True)
    (asset_cache_dir / "0025.png").write_bytes(b"sprite-bytes")

    icons_dir = output_dir / "images" / "icons" / "types"
    icons_dir.mkdir(parents=True, exist_ok=True)
    (icons_dir / "fire.png").write_bytes(b"icon-bytes")

    resolved = sprites.copy_sprites(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        asset_cache_dir=asset_cache_dir,
    )

    assert resolved == {"pikachu": "images/pikachu.png"}
    assert (icons_dir / "fire.png").read_bytes() == b"icon-bytes"
