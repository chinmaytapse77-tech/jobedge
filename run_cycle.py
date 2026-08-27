#!/usr/bin/env python3
"""Entry point: python run_cycle.py"""

from jobedge.config import load_config
from jobedge.orchestrator import run_cycle

if __name__ == "__main__":
    run_cycle(load_config())
