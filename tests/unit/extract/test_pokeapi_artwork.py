"""Tests for pipelines/extract/pokeapi.py's high-resolution artwork path.

Kept separate from test_pokeapi.py because this path talks to PokéAPI's
sprite *repository* on GitHub rather than its JSON API, and writes binary
image bytes alongside its CSV — a different enough contract to be worth
reading on its own.
"""

import csv
import hashlib
import struct

import pytest
import requests

from pipelines.extract import pokeapi


def _png_bytes(width: int, height: int, *, trailer: bytes = b"rest-of-the-file") -> bytes:
    """A byte string with a valid PNG signature and IHDR width/height.

    Only the first 24 bytes are structurally meaningful to the extractor
    (it reads dimensions straight out of the header rather than decoding
    the image), so this is a real fixture rather than a stand-in.
    """
    return (
        b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + trailer
    )


class _FakeResponse:
    def __init__(self, *, content: bytes = b"", status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error


class _FakeSession:
    def __init__(self, *, content_by_url: dict[str, bytes], status_by_url: dict[str, int] = None):
        self._content_by_url = content_by_url
        self._status_by_url = status_by_url or {}
        self.requested_urls: list[str] = []

    def get(self, url, **_kwargs):
        self.requested_urls.append(url)
        status = self._status_by_url.get(url, 200 if url in self._content_by_url else 404)
        return _FakeResponse(content=self._content_by_url.get(url, b""), status_code=status)


def _read_rows(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _url(resource_id: str) -> str:
    return f"{pokeapi.ARTWORK_BASE_URL}/{resource_id}.png"


def test_writes_manifest_and_caches_image_bytes(tmp_path):
    render = _png_bytes(512, 512)
    session = _FakeSession(content_by_url={_url("10034"): render})
    output_path = tmp_path / "artwork.csv"
    cache_dir = tmp_path / "cache"

    pokeapi.extract_artwork(
        output_path,
        [("charizard-mega-x", "10034")],
        dataset_version="9.9.9",
        session=session,
        cache_dir=cache_dir,
    )

    rows = _read_rows(output_path)
    assert len(rows) == 1
    row = rows[0]
    # local_cache_path is keyed by form slug, not by resource id: the
    # dashboard and release layers both look assets up by pokemon_key.
    assert row["form_name"] == "charizard-mega-x"
    assert row["local_cache_path"] == "charizard-mega-x.png"
    assert row["pokeapi_resource_id"] == "10034"
    assert row["image_kind"] == "home_render"
    assert row["width"] == "512"
    assert row["height"] == "512"
    assert row["sha1"] == hashlib.sha1(render).hexdigest()
    assert row["file_size_bytes"] == str(len(render))
    assert row["source_url"] == _url("10034")
    assert row["source_record_id"] == "10034"
    assert row["dataset_version"] == "9.9.9"
    assert (cache_dir / "charizard-mega-x.png").read_bytes() == render


def test_uses_the_forms_own_resource_id_not_its_species_id(tmp_path):
    # The whole reason no mapping seed is needed: charizard-mega-x is
    # species 6 but resource 10034, and the sprite repo is keyed by the
    # latter. Fetching /6.png would silently return base Charizard's art.
    session = _FakeSession(content_by_url={_url("10034"): _png_bytes(512, 512)})

    pokeapi.extract_artwork(
        tmp_path / "artwork.csv",
        [("charizard-mega-x", "10034")],
        session=session,
        cache_dir=tmp_path / "cache",
    )

    assert session.requested_urls == [_url("10034")]


def test_skips_forms_with_no_published_render(tmp_path):
    session = _FakeSession(content_by_url={_url("25"): _png_bytes(512, 512)})
    output_path = tmp_path / "artwork.csv"

    pokeapi.extract_artwork(
        output_path,
        [("pikachu", "25"), ("some-cosmetic-form", "99999")],
        session=session,
        cache_dir=tmp_path / "cache",
    )

    # The 404 is skipped, not fatal, and not fabricated: the missing form
    # simply has no row, which is what the coverage gate then measures.
    assert [row["form_name"] for row in _read_rows(output_path)] == ["pikachu"]


def test_skips_responses_that_are_not_png(tmp_path):
    session = _FakeSession(content_by_url={_url("25"): b"<html>rate limited</html>"})
    output_path = tmp_path / "artwork.csv"
    cache_dir = tmp_path / "cache"

    pokeapi.extract_artwork(output_path, [("pikachu", "25")], session=session, cache_dir=cache_dir)

    assert _read_rows(output_path) == []
    assert not (cache_dir / "pikachu.png").exists()


def test_reuses_a_cached_file_without_refetching(tmp_path):
    cached = _png_bytes(512, 512, trailer=b"cached-copy")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "pikachu.png").write_bytes(cached)
    session = _FakeSession(content_by_url={})

    pokeapi.extract_artwork(
        tmp_path / "artwork.csv",
        [("pikachu", "25")],
        session=session,
        cache_dir=cache_dir,
    )

    assert session.requested_urls == []
    assert _read_rows(tmp_path / "artwork.csv")[0]["sha1"] == hashlib.sha1(cached).hexdigest()


def test_skip_existing_false_refetches(tmp_path):
    fresh = _png_bytes(512, 512, trailer=b"fresh-copy")
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "pikachu.png").write_bytes(_png_bytes(512, 512, trailer=b"stale"))
    session = _FakeSession(content_by_url={_url("25"): fresh})

    pokeapi.extract_artwork(
        tmp_path / "artwork.csv",
        [("pikachu", "25")],
        session=session,
        cache_dir=cache_dir,
        skip_existing=False,
    )

    assert session.requested_urls == [_url("25")]
    # And the refetched bytes actually replace the stale ones -- a manifest
    # describing the fresh file beside a cache still holding the old one
    # would be worse than not refetching at all.
    assert (cache_dir / "pikachu.png").read_bytes() == fresh


@pytest.mark.parametrize(
    "data",
    [b"", b"not-a-png-at-all", b"\x89PNG\r\n\x1a\n" + b"too-short"],
    ids=["empty", "wrong-signature", "truncated-header"],
)
def test_png_dimensions_rejects_non_png_payloads(data):
    assert pokeapi._png_dimensions(data) is None


def test_png_dimensions_reads_the_ihdr_header():
    assert pokeapi._png_dimensions(_png_bytes(475, 300)) == (475, 300)
