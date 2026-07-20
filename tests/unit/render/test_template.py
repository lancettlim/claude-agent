from pipelines.render.data_source import CardModel, CardSlot
from pipelines.render.template import render_html


class _FakeResponse:
    def __init__(self, content: bytes = b"\x89PNG fake icon bytes"):
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    """Icon downloads always "succeed" with fixed bytes, so render_html
    never makes a real network call during tests."""

    def __init__(self):
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: int = 30):
        self.requested_urls.append(url)
        return _FakeResponse()


def _card():
    return CardModel(
        team_name="Test Team",
        subtitle="US",
        slots=[
            CardSlot(
                slot_number=1,
                pokemon_name="Incineroar",
                form_name="incineroar",
                item_name="Sitrus Berry",
                ability="Intimidate",
                nature="Impish",
                tera_type="Ghost",
                moves=["Fake Out", "Flare Blitz"],
                move_types=["normal", "fire"],
            )
        ],
    )


def test_render_html_includes_slot_content(tmp_path):
    html = render_html(_card(), icon_cache_dir=tmp_path, session=_FakeSession())

    assert "Test Team" in html
    assert "US" in html
    assert "Incineroar" in html
    assert "Sitrus Berry" in html
    assert "Intimidate" in html
    assert "Impish" in html
    assert "Tera Ghost" in html
    assert "Fake Out" in html
    assert "Flare Blitz" in html


def test_render_html_caches_icons_between_slots_with_same_type(tmp_path):
    card = CardModel(
        team_name="T",
        slots=[
            CardSlot(1, "A", "a", moves=["Move One"], move_types=["fire"]),
            CardSlot(2, "B", "b", moves=["Move Two"], move_types=["fire"]),
        ],
    )
    session = _FakeSession()

    render_html(card, icon_cache_dir=tmp_path, session=session)

    fire_icon_requests = [u for u in session.requested_urls if u.endswith("/10.png")]
    assert len(fire_icon_requests) == 1


def test_render_html_handles_missing_optional_fields(tmp_path):
    card = CardModel(
        team_name="T",
        slots=[CardSlot(slot_number=1, pokemon_name="A", form_name="a", moves=[], move_types=[])],
    )

    html = render_html(card, icon_cache_dir=tmp_path, session=_FakeSession())

    assert "T" in html
    assert "A" in html
