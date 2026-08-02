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


def test_track_requests_counts_one_logical_request_per_successful_call():
    session = _FlakySession(fail_count=0)

    with http.track_requests() as stats:
        http.get_with_retry(session, "https://example.test/a", timeout=30)
        http.get_with_retry(session, "https://example.test/b", timeout=30)

    assert stats.attempted == 2
    assert stats.succeeded == 2
    assert stats.success_rate == 1.0
    assert stats.failed_urls == []


def test_track_requests_counts_retried_call_as_one_attempt(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _FlakySession(fail_count=2, status_code=503)

    with http.track_requests() as stats:
        http.get_with_retry(session, "https://example.test/x", timeout=30)

    # 3 raw HTTP calls happened (2 failures + 1 success), but that's one
    # logical get_with_retry call, so it counts as a single attempt.
    assert session.calls == 3
    assert stats.attempted == 1
    assert stats.succeeded == 1


def test_track_requests_records_failure_after_exhausting_attempts(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _AlwaysFailingSession(status_code=500)

    with http.track_requests() as stats:
        try:
            http.get_with_retry(session, "https://example.test/x", timeout=30, attempts=2)
        except requests.exceptions.HTTPError:
            pass

    assert stats.attempted == 1
    assert stats.succeeded == 0
    assert stats.success_rate == 0.0
    assert stats.failed_urls == ["https://example.test/x"]


def test_track_requests_records_failure_on_immediate_4xx(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda seconds: None)
    session = _AlwaysFailingSession(status_code=404)

    with http.track_requests() as stats:
        try:
            http.get_with_retry(session, "https://example.test/x", timeout=30)
        except requests.exceptions.HTTPError:
            pass

    assert stats.attempted == 1
    assert stats.succeeded == 0
    assert session.calls == 1


def test_get_with_retry_outside_track_requests_does_not_raise():
    session = _FlakySession(fail_count=0)

    # No active track_requests() scope -- must be a safe no-op, not an error.
    response = http.get_with_retry(session, "https://example.test/x", timeout=30)

    assert response.json() == {"ok": True}


def test_request_stats_success_rate_none_when_nothing_attempted():
    stats = http.RequestStats()

    assert stats.success_rate is None
