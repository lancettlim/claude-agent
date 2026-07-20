import requests

from pipelines.render import assets


class _FakeResponse:
    def __init__(self, content: bytes = b"fake-icon-bytes"):
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _FailingResponse:
    def raise_for_status(self) -> None:
        raise requests.HTTPError("404")


class _FakeSession:
    def __init__(self, *, fail: bool = False):
        self.requested_urls: list[str] = []
        self.fail = fail

    def get(self, url: str, timeout: int = 30):
        self.requested_urls.append(url)
        return _FailingResponse() if self.fail else _FakeResponse()


def test_ensure_type_icon_downloads_and_caches(tmp_path):
    session = _FakeSession()

    path = assets.ensure_type_icon("fire", cache_dir=tmp_path, session=session)

    assert path == tmp_path / "types" / "fire.png"
    assert path.read_bytes() == b"fake-icon-bytes"
    assert session.requested_urls == [f"{assets.TYPE_ICON_BASE_URL}/10.png"]

    # second call should hit the cache, not the network
    assets.ensure_type_icon("fire", cache_dir=tmp_path, session=session)
    assert len(session.requested_urls) == 1


def test_ensure_type_icon_returns_none_for_unknown_type(tmp_path):
    assert assets.ensure_type_icon("not-a-type", cache_dir=tmp_path, session=_FakeSession()) is None


def test_ensure_type_icon_returns_none_on_download_failure(tmp_path):
    session = _FakeSession(fail=True)

    assert assets.ensure_type_icon("water", cache_dir=tmp_path, session=session) is None


def test_ensure_item_icon_slugifies_and_downloads(tmp_path):
    session = _FakeSession()

    path = assets.ensure_item_icon("Choice Scarf", cache_dir=tmp_path, session=session)

    assert path == tmp_path / "items" / "choice-scarf.png"
    assert session.requested_urls == [f"{assets.ITEM_ICON_BASE_URL}/choice-scarf.png"]


def test_ensure_item_icon_returns_none_on_download_failure(tmp_path):
    session = _FakeSession(fail=True)

    assert assets.ensure_item_icon("Some Rare Item", cache_dir=tmp_path, session=session) is None
