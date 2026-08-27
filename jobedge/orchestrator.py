"""Orchestrator: reads state, decides a plan, and delegates to registered
agents. Never fetches or scores directly — every unit of work happens inside
an Agent (see jobedge/agents/).
"""

from __future__ import annotations

import time

from jobedge import storage
from jobedge.agents.base import Agent, AgentResult
from jobedge.agents.mock_fetchers import MockFetcher
from jobedge.agents.real_fetchers import SourceFetcher
from jobedge.config import Config
from jobedge.sources import base as sources_base
from jobedge.sources import eluta, job_bank  # noqa: F401 - import registers them

MOCKED_SOURCES = ("company_pages", "eluta", "indeed", "linkedin")


def _build_registry(config: Config) -> dict[str, callable]:
    """Registry pattern: swap mock for real fetchers with one config flag
    (use_mock_fetcher) rather than editing this file per source."""
    if config.use_mock_fetcher:
        return {name: (lambda n=name: MockFetcher(n)) for name in MOCKED_SOURCES}
    return {name: (lambda cls=cls: SourceFetcher(cls())) for name, cls in sources_base.SOURCES.items()}

SCORER_STATUS = "not implemented yet (Prompt 5)"
GAP_ANALYZER_STATUS = "not implemented yet (Prompt 6)"

_RULE = "=" * 60


def run_cycle(config: Config) -> None:
    storage.init_db(config.db_path)
    print(f"\n{_RULE}\nJOBEDGE CYCLE START — {storage.utcnow_iso()}\n{_RULE}")

    registry = _build_registry(config)
    mode = "mock" if config.use_mock_fetcher else "real"
    _print_state(config)
    _print_plan(config, registry, mode)

    results = [_run_source(config, registry, source) for source in config.sources]

    _print_summary(config, results)


def _print_state(config: Config) -> None:
    print("\n-- Current state --")
    for source in config.sources:
        last = storage.last_fetch_time(config.db_path, source)
        print(f"  {source:<16} last successful fetch: {last or 'never'}")
    for profile in config.profiles:
        unscored = storage.count_unscored(config.db_path, profile.name)
        print(f"  {profile.name:<16} unscored listings: {unscored}")


def _print_plan(config: Config, registry: dict, mode: str) -> None:
    print(f"\n-- Plan ({mode} fetchers) --")
    for source in config.sources:
        if source in registry:
            print(f"  [run]  {source:<16} fetcher registered ({mode})")
        else:
            print(f"  [skip] {source:<16} no fetcher registered yet")
    print(f"  [skip] scorer            {SCORER_STATUS}")
    print(f"  [skip] gap_analyzer      {GAP_ANALYZER_STATUS}")


def _run_source(config: Config, registry: dict, source: str) -> AgentResult:
    started_at = storage.utcnow_iso()
    factory = registry.get(source)

    if factory is None:
        result = AgentResult(
            agent=source, status="failed", records_touched=0,
            notes="no fetcher registered yet",
        )
    else:
        print(f"\n-- Running {source} (delay {config.request_delay_seconds}s) --")
        time.sleep(config.request_delay_seconds)
        result = factory().run(config, config.db_path)
        print(f"  {result.status.upper():<7} records_touched={result.records_touched}  {result.notes}")

    storage.log_cycle(
        config.db_path,
        agent=source,
        started_at=started_at,
        finished_at=storage.utcnow_iso(),
        records_touched=result.records_touched,
        status=result.status,
        notes=result.notes,
    )
    return result


def _print_summary(config: Config, results: list[AgentResult]) -> None:
    print(f"\n{_RULE}\nCYCLE SUMMARY\n{_RULE}")
    print("-- By source --")
    for result in results:
        print(f"  {result.agent:<16} {result.status:<7} new_records={result.records_touched:<3} {result.notes}")
    print("\n-- By profile --")
    for profile in config.profiles:
        unscored = storage.count_unscored(config.db_path, profile.name)
        print(f"  {profile.name:<16} unscored listings: {unscored:<4} (scorer {SCORER_STATUS})")
    print(f"{_RULE}\nJOBEDGE CYCLE END\n{_RULE}\n")
