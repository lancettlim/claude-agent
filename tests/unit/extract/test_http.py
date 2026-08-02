import requests

from pipelines.extract import http


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error

    def json(self):
        return self._payload


class _FlakySession:
    """Fails with the given status code `fail_count` times, then succeeds."""

    def __init__(self, *, fail_count: int, status_code: int = 500) -> None:
        self._fail_count = fail_count
        self._status_code = status_code
        self.calls = 0

    def get(self, url: str, timeout: int):
        self.calls += 1
        if self.calls <= self._fail_count:
            return _FakeResponse(status_code=self._status_code)
        return _FakeResponse(payload={"ok": True})


class _AlwaysFailingSession:
    def __init__(self, *, status_code: int) -> None:
        self._status_code = status_code
        self.calls = 0

    def get(self, url: str, timeout: int):
        self.calls += 1
        return _FakeResponse(status_code=self._status_code)


def test_get_with_retry_returns_response_on_first_success():
    session = _FlakySession(fail_count=0)

    response = http.get_with_retry(session, "https://example.test/x", timeout=30)

    assert response.json() == {"ok": True}
    assert session.calls == 1


def test_get_with_retry_retries_transient_5xx_then_succeeds(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _FlakySession(fail_count=2, status_code=503)

    response = http.get_with_retry(session, "https://example.test/x", timeout=30)

    assert response.json() == {"ok": True}
    assert session.calls == 3


def test_get_with_retry_raises_after_exhausting_attempts(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _AlwaysFailingSession(status_code=500)

    try:
        http.get_with_retry(session, "https://example.test/x", timeout=30, attempts=3)
        raised = False
    except requests.exceptions.HTTPError:
        raised = True

    assert raised
    assert session.calls == 3


def test_get_with_retry_does_not_retry_client_errors(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _AlwaysFailingSession(status_code=404)

    try:
        http.get_with_retry(session, "https://example.test/x", timeout=30)
        raised = False
    except requests.exceptions.HTTPError:
        raised = True

    assert raised
    assert session.calls == 1


def test_get_with_retry_backs_off_with_increasing_delay(monkeypatch):
    delays = []
    monkeypatch.setattr(http.time, "sleep", lambda seconds: delays.append(seconds))
    session = _AlwaysFailingSession(status_code=500)

    try:
        http.get_with_retry(session, "https://example.test/x", timeout=30, attempts=3)
    except requests.exceptions.HTTPError:
        pass

    assert delays == [2.0, 4.0]
