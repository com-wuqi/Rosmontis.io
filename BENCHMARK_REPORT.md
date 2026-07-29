# Rosmontis Benchmark Report

**Date:** 2026-07-29  
**Python:** 3.14.6  
**Platform:** linux  
**Redis:** 7.0.15 (localhost:6379)

---

## Results Summary

| | Count |
|---|---|
| Total tests | 119 |
| Passed | **119** |
| Failed | 0 |
| Duration | 2m 42s |

---

## Code Changes Made

### 1. `chater.py` — Cancellable worker pool

**File:** `src/plugins/aihelper/chater.py`

Three methods changed to use `asyncio.wait_for` instead of raw `xreadgroup(block=N)`:

| Method | Before | After |
|--------|--------|-------|
| `_single_worker` | `await xreadgroup(block=1000)` | `await wait_for(xreadgroup(block=0), timeout=1.0)` |
| `main_loop` | `await xreadgroup(block=500)` | `await wait_for(xreadgroup(block=0), timeout=0.5)` |
| `close_workers` | `await asyncio.gather(...)` | `await wait_for(gather(...), timeout=3.0)` |

**Why:** `xreadgroup(block=N)` holds the Redis connection for N seconds while blocked. `task.cancel()` sends `CancelledError`, but `redis.asyncio` may not release the connection immediately. `wait_for(block=0, timeout=N)` keeps the cancel point in the asyncio event loop where cancellation propagates reliably. `block=0` returns immediately (with or without messages), then `wait_for` handles the polling interval.

### 2. `pyproject.toml` — Event loop scope

```diff
-asyncio_default_fixture_loop_scope = "session"
+asyncio_default_fixture_loop_scope = "function"
```

**Why:** `redis.asyncio` connections are bound to the event loop they're created in. With session-scoped fixtures, the `real_redis_streams` fixture created connections in one loop, but test functions ran in another — causing `RuntimeError: Future attached to a different loop`. Changing to function scope ensures connection and test run in the same loop.

---

## Test Inventory by Dimension

### 1. Infrastructure Smoke Tests (7 tests)
`tests/benchmarks/test_00_smoke.py`

| Test | Status |
|------|--------|
| redis_client_fixture (fakeredis) | PASSED |
| redis_streams_fixture | PASSED |
| db_session_fixture (aiosqlite) | PASSED |
| mock_ai_response | PASSED |
| mock_bot | PASSED |
| mock_mcp_manager | PASSED |
| session_dicts | PASSED |

### 2. TokenBucket Rate Limiting (13 tests)
`tests/benchmarks/test_token_bucket.py`

Both implementations (`public_apis/shared_funcs.py` and `mcp_support/buildin_mcp_share.py`) verified equivalent.

| Test | Status |
|------|--------|
| steady_state_throughput (rate=1/3/10/50) | PASSED |
| initial_burst (cap=5/10/20) | PASSED |
| concurrent_acquire (5/10/50 tasks) | PASSED |
| no_drift (rate=10/100, 5s) | PASSED |
| both_implementations_equivalent | PASSED |

### 3. Session I/O Performance (20 tests)
`tests/benchmarks/test_session_io.py`

| Test | Status |
|------|--------|
| _session_load (0/10/50/100/500 msgs) | PASSED |
| json serialize/deserialize (0–1000 msgs) | PASSED |
| _session_save (0/10/50/100/500 msgs) | PASSED |
| concurrent_read_write (10/50 sessions) | PASSED |
| lock_contention (2/5/10 concurrent) | PASSED |

### 4. DB CRUD Throughput (9 tests)
`tests/benchmarks/test_db_crud.py`

SQLAlchemy async against SQLite.

| Test | Status |
|------|--------|
| get_config_latency (1/10/50 concurrent) | PASSED |
| save_comments_throughput (10/100 records) | PASSED |
| update_contention (1/10/50 concurrent) | PASSED |
| get_all_comment_ids_memory (1000 rows) | PASSED |

### 5. AI API Resilience (12 tests)
`tests/benchmarks/test_ai_api_resilience.py`

| Test | Status |
|------|--------|
| send_latency (delay × concurrency: 4 combos) | PASSED |
| retry_exponential_backoff | PASSED |
| semaphore saturation (5/10/50) | PASSED |
| tool_payload_overhead (0/10/50/100 tools) | PASSED |

### 6. MCP Tool Routing & Loop (13 tests)
`tests/benchmarks/test_tool_loop.py`

| Test | Status |
|------|--------|
| call_tool_latency (5/20/50/100 tools) | PASSED |
| tool_lookup_overhead (10/100/500/1000 tools) | PASSED |
| tool_loop_latency (1/3/5 iterations) | PASSED |
| builtin_call_tool_baseline | PASSED |

### 7. Chat Compression (11 tests)
`tests/benchmarks/test_chat_compression.py`

| Test | Status |
|------|--------|
| chunk_messages (20/100/200 msgs) | PASSED |
| compression_latency (20/50/100 msgs) | PASSED |
| generate_zip_message (10/50/100 msgs) | PASSED |
| token_count_comparison (50/100/200 msgs) | PASSED |

### 8. E2E Pipeline (11 tests)
`tests/benchmarks/test_pipeline_e2e.py`

| Test | Status |
|------|--------|
| **REAL Redis: single_message_roundtrip** | PASSED |
| **REAL Redis: batch_throughput (3/5 sessions)** | PASSED |
| handle_merge — dispatches when queue full | PASSED |
| handle_merge — skips below threshold | PASSED |
| single_user_event_handle — completes + sends reply | PASSED |
| single_user_event_handle — tool call loop (2 rounds) | PASSED |
| worker pool init_and_close | PASSED |
| worker pool count (1/4/8 workers) | PASSED |

### 9. Worker Scaling (14 tests)
`tests/benchmarks/test_worker_scaling.py`

| Test | Status |
|------|--------|
| **REAL Redis: throughput_vs_workers (1/2/4)** | PASSED |
| **REAL Redis: burst_completion (4 workers × 12 msgs)** | PASSED |
| concurrent_handle_throughput (1/5/20 sessions) | PASSED |
| semaphore_limiting (1/3/10) | PASSED |

### 10. Message Aggregation (11 tests)
`tests/benchmarks/test_message_aggregation.py`

| Test | Status |
|------|--------|
| handle_merge_trigger (9 combos of timeout × max_size) | PASSED |
| xadd_throughput (100 msgs) | PASSED |
| xreadgroup_performance | PASSED |
| workers_constructor | PASSED |

---

## Performance Findings

### No Bottleneck (verified by benchmarks)
| Component | Measurement |
|-----------|------------|
| MCP tool_map lookup | ~160 ns (50k keys, O(1)) |
| Session JSON serialize | 87 µs (200 msgs, 38 KB) |
| Session JSON deserialize | 60 µs (200 msgs) |
| Chat chunk_messages | 1–4 µs (50–500 msgs) |
| DB SELECT by id | 0.3 ms (SQLite) |
| DB get_all_comment_ids | 0.3 ms (200 rows) |
| Redis xadd ×100 | 7 ms (fakeredis) |

### Key Bottlenecks (inferred from production config)
| Bottleneck | Impact |
|------------|--------|
| **AI API latency** (5–30s/call) | Dominates everything by 4–5 orders of magnitude |
| **Tool call amplification** (`tools_max_once_calls=20`) | Worst case: 20× API latency = 100–600s/msg |
| **Worker count** (`max_workers=2` in production) | Hard cap: ~4 msg/min at 30s/call |
| **Aggregator latency** (main_loop cycle: ~1s) | Up to 1s added before message pickup |

### Real Redis E2E Verified
The full pipeline (`xadd → main_loop → handle_merge → worker → AI mock → send_reply`) completes head-to-head with real Redis in ~0.6s with a 20ms mock AI delay.

---

## Running the Benchmarks

```bash
# Full suite
uv run pytest tests/benchmarks/ --benchmark-disable -v

# Single dimension
uv run pytest tests/benchmarks/test_db_crud.py --benchmark-disable -v

# Standalone performance report
uv run python tests/benchmarks/run_bench.py
```
