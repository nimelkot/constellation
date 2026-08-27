"""A deterministic local worker for trying the orchestration UI."""

from __future__ import annotations

import time
from collections.abc import Iterator

from constellation.core.orchestrator import AgentNode


def demo_worker(node: AgentNode) -> Iterator[str]:
    """Yield a small mission lifecycle without requiring an external model."""
    steps = (
        f"Mission received: {node.prompt}",
        "Charting a plan and identifying dependencies",
        "Running local analysis pass",
        "Collecting results for the signal stream",
    )
    for step in steps:
        time.sleep(0.35)
        yield step
