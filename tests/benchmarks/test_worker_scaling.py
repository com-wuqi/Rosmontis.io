"""Benchmark: Worker pool throughput vs max_workers.

NOTE: These tests require a real Redis instance and full NoneBot bot driver.
They are skipped by default. To run, set REAL_REDIS_URL and provide a proper
NoneBot bot instance.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="Worker scaling requires real Redis + full NoneBot driver. "
    "Run with REAL_REDIS_URL set and a proper bot instance."
)
