"""The ONLY module in JobEdge that performs an HTTP request (steering rule 12).

Every Source calls get_html/get_json here instead of touching `requests`
directly, so timeout, retry, backoff, and User-Agent apply uniformly.
"""

from __future__ import annotations

import time

import requests

DEFAULT_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
USER_AGENT = (
    "JobEdgeBot/1.0 (+https://github.com/chinmaytapse77-tech/jobedge; "
    "personal job-search agent, contact: chinmaytapse77@gmail.com)"
)


class SourceError(Exception):
    """Raised when a request fails after all retries. Sources should catch
    this (or let it propagate to the Fetcher's own isolation boundary) —
    never let it crash the whole cycle."""


def _request(method: str, url: str, *, params: dict | None, headers: dict | None) -> requests.Response:
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.request(
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
