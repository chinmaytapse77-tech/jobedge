"""Job Bank (jobbank.gc.ca) — public search results. No signup, no key, free.

UNVERIFIED against live markup: this sandbox's egress policy blocks
jobbank.gc.ca outright, so these selectors could not be tested against the
real page. Run the verification one-liner locally where you have real
internet access. If 0 listings survive parsing, the CSS selectors below
are stale — paste back the raw HTML of one result card (print(cards[0]) in
_parse) rather than guessing, and this gets fixed in one pass.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"
MAX_PAGES = 3

_debug_card_printed = False


@register
class JobBankSource(Source):
    name = "job_bank"

    def fetch(self, config: Config) -> list[dict]:
        return search_all_locations(config, self.name, _search)


def _search(keywords: str | None, city: str) -> list[dict]:
    """Raises on request failure -- search_all_locations decides whether
    that's a one-location blip or the whole source being unreachable."""
    rows: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        params = {"locationstring": city, "page": page}
        if keywords:
            params["searchstring"] = keywords
        html = get_html(SEARCH_URL, params=params)
        page_rows = _parse(html)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str) -> list[dict]:
    global _debug_card_printed
    soup = BeautifulSoup(html, "html.parser")
    cards = (
        soup.select("article.resultJobItem")
        or soup.select("div.resultJobItem")
        or soup.select("a[href*='/jobsearch/jobposting/']")
    )
    if cards and not _debug_card_printed:
        # One-time real-markup dump so the next fix is exact, not another
        # guess (same idea as the class doc's "print the raw result" rule).
        print(f"  job_bank: DEBUG first card raw HTML:\n{str(cards[0])[:3000]}")
        _debug_card_printed = True
    rows = []
    for card in cards:
        link = card if card.name == "a" else card.select_one("a[href*='/jobsearch/jobposting/']")
        if link is None:
            continue
        href = link.get("href", "")
        url = href if href.startswith("http") else f"https://www.jobbank.gc.ca{href}"
        external_id = href.rstrip("/").split("/")[-1] or url
        title_el = card.select_one(".noctitle, h3, h4") or link
        company_el = card.select_one(".business")
        location_el = card.select_one(".location")
        rows.append(
            normalize_row(
                source="job_bank",
                external_id=external_id,
                title=_strip_label(title_el.get_text(strip=True) if title_el else None, "Job Bank"),
                company=company_el.get_text(strip=True) if company_el else None,
                location=_strip_label(location_el.get_text(strip=True) if location_el else None, "Location"),
                url=url,
                description=None,
                posted_at=None,
                raw=str(card)[:2000],
            )
        )
    if cards and not rows:
        print("  job_bank: found result cards but couldn't extract a URL from any — selectors are stale")
    return rows


def _strip_label(text: str | None, label: str) -> str | None:
    """Job Bank's card markup glues badge/status text (e.g. 'New', 'Direct
    Apply', a 'Posted on Job Bank...' disclaimer, or the literal word
    'Location') onto the front of the real value with no separator, and
    the real value reliably starts right after the last occurrence of the
    trailing label. Confirmed against real output from a live run."""
    if not text:
        return text
    if label in text:
        text = text.rsplit(label, 1)[-1]
    return text.strip() or None
