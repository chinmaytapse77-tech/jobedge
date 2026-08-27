"""Base interface every JobEdge agent (fetcher, scorer, gap analyzer) implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from jobedge.config import Config

AgentStatus = Literal["ok", "failed", "blocked"]


@dataclass
class AgentResult:
    agent: str
    status: AgentStatus
    records_touched: int
    notes: str = ""


class Agent(ABC):
    """One unit of work in a cycle. The orchestrator calls run(); it never
    fetches, scores, or touches storage internals itself."""

    name: str

    @abstractmethod
    def run(self, config: Config, db_path: str) -> AgentResult:
        raise NotImplementedError
