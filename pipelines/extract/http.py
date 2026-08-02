"""Shared HTTP retry/backoff helper for pipelines/extract/*.

Every extractor's raw HTTP calls (list/detail fetches, page scrapes, image
downloads) used to call `session.get(...).raise_for_status()` directly, so a
single transient failure -- a 5xx response, a dropped connection, a timeout
-- partway through a run aborted the whole extraction with no output at all.
That's expensive for PokéAPI's roughly 1,350 sequential requests per run in
particular. `get_with_retry` centralizes retry-with-exponential-backoff (the
pattern pokeapi.py's move/ability/item lookups already had one bespoke copy
of) so every extractor's request path gets it uniformly.
"""

from __future__ import annotations

import sys
import time

import requests

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0


def get_with_retry(
    session: requests.Session,
    url: str,
    *,
    attempts: int = DEFAULT_RETRY_ATTEMPTS,
    backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    **kwargs,
) -> requests.Response:
    """GET url, retrying transient failures (connection errors, timeouts, 5xx
    responses) with exponential backoff. A 4xx response fails immediately --
    retrying a client error just burns the backoff window on a request that
    will never succeed.

    Raises the last exception once `attempts` is exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code < 500:
                raise
            last_exc = exc
        except requests.exceptions.RequestException as exc:
            last_exc = exc
        if attempt < attempts - 1:
            delay = backoff_seconds * (2**attempt)
            print(
                f"Transient error fetching {url} "
                f"(attempt {attempt + 1}/{attempts}): {last_exc}; retrying in {delay:.0f}s",
                file=sys.stderr,
            )
            time.sleep(delay)
    raise last_exc
