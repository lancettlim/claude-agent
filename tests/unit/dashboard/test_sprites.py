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
        [{"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"}],
    )
    assert sprites.load_asset_map(tmp_path) == {"pikachu": "0025.png"}


def test_copy_sprites_copies_resolvable_keys(tmp_path):
    normalized_dir = tmp_path / "normalized"
    asset_cache_dir = tmp_path / "asset_cache"
    output_dir = tmp_path / "out"
    _write_csv(
        normalized_dir / "pokemon_asset.csv",
        [{"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"}],
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
        [{"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"}],
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
            {"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"},
            {"pokemon_key": "raichu", "image_kind": "menu_sprite", "local_cache_path": "0026.png"},
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
        [{"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"}],
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


# --- image_kind separation and hero art ---


def _both_kinds_asset_csv(path):
    """pokemon_asset carries one row per Pokémon per image_kind — the shape
    that makes an unfiltered pokemon_key lookup ambiguous."""
    _write_csv(
        path,
        [
            {"pokemon_key": "pikachu", "image_kind": "menu_sprite", "local_cache_path": "0025.png"},
            {
                "pokemon_key": "pikachu",
                "image_kind": "home_render",
                "local_cache_path": "pikachu.png",
            },
        ],
    )


def test_load_asset_map_separates_the_two_image_kinds(tmp_path):
    # Without the image_kind filter these two rows collapse onto one key and
    # whichever came last wins, silently pointing menu-sprite lookups at
    # artwork filenames.
    _both_kinds_asset_csv(tmp_path / "pokemon_asset.csv")

    assert sprites.load_asset_map(tmp_path) == {"pikachu": "0025.png"}
    assert sprites.load_asset_map(tmp_path, image_kind="menu_sprite") == {"pikachu": "0025.png"}
    assert sprites.load_asset_map(tmp_path, image_kind="home_render") == {"pikachu": "pikachu.png"}


def _write_png(path, size):
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (size, size), (10, 20, 30, 255)).save(path, "PNG")


def test_copy_hero_art_downscales_to_webp(tmp_path):
    normalized_dir = tmp_path / "normalized"
    artwork_cache_dir = tmp_path / "artwork"
    output_dir = tmp_path / "out"
    _both_kinds_asset_csv(normalized_dir / "pokemon_asset.csv")
    _write_png(artwork_cache_dir / "pikachu.png", 512)

    resolved = sprites.copy_hero_art(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        artwork_cache_dir=artwork_cache_dir,
        size_px=256,
    )

    assert resolved == {"pikachu": "images/hero/pikachu.webp"}
    dest = output_dir / "images" / "hero" / "pikachu.webp"
    assert dest.exists()

    from PIL import Image

    with Image.open(dest) as image:
        assert image.format == "WEBP"
        assert image.size == (256, 256)
    # The point of downscaling: a 256px WebP is a fraction of the 512px PNG.
    assert dest.stat().st_size < (artwork_cache_dir / "pikachu.png").stat().st_size


def test_copy_hero_art_skips_keys_with_no_render(tmp_path):
    normalized_dir = tmp_path / "normalized"
    output_dir = tmp_path / "out"
    _both_kinds_asset_csv(normalized_dir / "pokemon_asset.csv")

    # Manifest row exists but the cached file doesn't — skipped, not raised,
    # so a partial artwork cache still produces a working dashboard.
    resolved = sprites.copy_hero_art(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        artwork_cache_dir=tmp_path / "empty",
    )

    assert resolved == {}


def test_copy_hero_art_prunes_stale_renders_without_clobbering_siblings(tmp_path):
    # Mirrors test_copy_sprites_does_not_clobber_sibling_asset_subdirectories:
    # images/hero/ is pruned by name, never rmtree'd, so build.py's other
    # image subdirectories survive regardless of call order.
    normalized_dir = tmp_path / "normalized"
    artwork_cache_dir = tmp_path / "artwork"
    output_dir = tmp_path / "out"
    _both_kinds_asset_csv(normalized_dir / "pokemon_asset.csv")
    _write_png(artwork_cache_dir / "pikachu.png", 512)

    hero_dir = output_dir / "images" / "hero"
    hero_dir.mkdir(parents=True, exist_ok=True)
    (hero_dir / "dropped-mon.webp").write_bytes(b"stale")
    sibling = output_dir / "images" / "icons" / "types"
    sibling.mkdir(parents=True, exist_ok=True)
    (sibling / "fire.png").write_bytes(b"type-icon")

    sprites.copy_hero_art(
        {"pikachu"},
        output_dir=output_dir,
        normalized_dir=normalized_dir,
        artwork_cache_dir=artwork_cache_dir,
    )

    assert not (hero_dir / "dropped-mon.webp").exists()
    assert (hero_dir / "pikachu.webp").exists()
    assert (sibling / "fire.png").read_bytes() == b"type-icon"
