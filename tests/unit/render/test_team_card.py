from pipelines.render import team_card
from pipelines.render.data_source import CardModel, CardSlot


class _FakePage:
    def __init__(self):
        self.content_set = None
        self.screenshot_path = None

    def set_content(self, html, wait_until=None):
        self.content_set = html

    def locator(self, selector):
        return self

    def screenshot(self, path):
        self.screenshot_path = path


class _FakeBrowser:
    def __init__(self):
        self.page = _FakePage()
        self.closed = False

    def new_page(self, viewport=None):
        return self.page

    def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self):
        self.browser = _FakeBrowser()
        self.launch_kwargs = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self.browser


class _FakePlaywrightContext:
    def __init__(self, chromium):
        self.chromium = chromium

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_render_screenshots_rendered_html_to_output_path(tmp_path, monkeypatch):
    fake_chromium = _FakeChromium()
    monkeypatch.setattr(team_card, "sync_playwright", lambda: _FakePlaywrightContext(fake_chromium))
    monkeypatch.setattr(
        team_card.template, "render_html", lambda card, **kwargs: "<html>fake</html>"
    )

    card = CardModel(team_name="T", slots=[CardSlot(1, "A", "a")])
    output_path = tmp_path / "out" / "card.png"

    team_card.render(card, output_path)

    assert fake_chromium.browser.page.content_set == "<html>fake</html>"
    assert fake_chromium.browser.page.screenshot_path == str(output_path)
    assert fake_chromium.browser.closed is True
    assert output_path.parent.exists()
