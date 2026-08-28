"""The ONLY module in JobEdge that performs an HTTP request (steering rule 12).

Every Source calls get_html/get_json here instead of touching `requests`
directly, so timeout, retry, backoff, and User-Agent apply uniformly.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

DEFAULT_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
MIN_SECONDS_BETWEEN_REQUESTS = 1.0
USER_AGENT = (
    "JobEdgeBot/1.0 (+https://github.com/chinmaytapse77-tech/jobedge; "
    "personal job-search agent, contact: chinmaytapse77@gmail.com)"
)

# Per-host last-request timestamp, so "at most 1 request per second per
# source" (steering rule 15) holds even when a Source makes several calls
# in a row (pagination, multiple locations/keywords) -- not just between
# different sources, which the orchestrator already paces separately.
_last_request_at: dict[str, float] = {}


class SourceError(Exception):
    """Raised when a request fails after all retries. Sources should catch
    this (or let it propagate to the Fetcher's own isolation boundary) —
    never let it crash the whole cycle."""


class _CompatTLSAdapter(HTTPAdapter):
    """Some sites (e.g. eluta.ca) run a narrower/older TLS cipher suite that
    OpenSSL 3.x's default SECLEVEL=2 rejects outright (SSLV3_ALERT_
    HANDSHAKE_FAILURE), even though a real browser connects fine. Lowering
    to SECLEVEL=1 widens the accepted cipher list to match what browsers
    still tolerate."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


_session = requests.Session()
_session.mount("https://", _CompatTLSAdapter())


def _wait_for_rate_limit(url: str) -> None:
    host = urlparse(url).netloc
    last = _last_request_at.get(host)
    if last is not None:
        elapsed = time.monotonic() - last
        remaining = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at[host] = time.monotonic()


def _request(method: str, url: str, *, params: dict | None, headers: dict | None) -> requests.Response:
    _wait_for_rate_limit(url)
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = _session.request(
                method, url, params=params, headers=merged_headers,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)

    raise SourceError(f"{method} {url} failed after {MAX_RETRIES + 1} attempt(s): {last_exc}") from last_exc


def get_json(url: str, params: dict | None = None, headers: dict | None = None) -> dict | list:
    return _request("GET", url, params=params, headers=headers).json()


def get_html(url: str, params: dict | None = None, headers: dict | None = None) -> str:
    return _request("GET", url, params=params, headers=headers).text
