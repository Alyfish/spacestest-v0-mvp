"""Utilities for opt-in E2E test mode and request tracing."""

from __future__ import annotations

import os
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Deque, Dict, List, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class E2EConfig:
    enabled: bool
    stub_mode: bool
    secret: str
    max_runs: int
    max_events_per_run: int
    default_user_id: str
    default_user_email: str


def load_e2e_config() -> E2EConfig:
    """Load E2E config from environment variables."""
    return E2EConfig(
        enabled=_env_bool("E2E_TEST_MODE", default=False),
        stub_mode=_env_bool("E2E_STUB_MODE", default=False),
        secret=(os.getenv("E2E_TEST_SECRET", "").strip()),
        max_runs=max(1, int(os.getenv("E2E_MAX_RUNS", "100") or "100")),
        max_events_per_run=max(
            1,
            int(os.getenv("E2E_MAX_EVENTS_PER_RUN", "500") or "500"),
        ),
        default_user_id=(os.getenv("E2E_DEFAULT_USER_ID", "e2e-user").strip()),
        default_user_email=(
            os.getenv("E2E_DEFAULT_USER_EMAIL", "e2e-user@spaces.local").strip()
        ),
    )


def is_secret_valid(config: E2EConfig, provided_secret: Optional[str]) -> bool:
    """Validate request secret for E2E-only features."""
    if not config.enabled or not config.secret:
        return False
    if provided_secret is None:
        return False
    return provided_secret.strip() == config.secret


def should_use_stub_mode(config: E2EConfig, provided_secret: Optional[str]) -> bool:
    """True only when stub mode is enabled and request is secret-authorized."""
    if not config.stub_mode:
        return False
    return is_secret_valid(config, provided_secret)


def normalize_path(path: str) -> str:
    """Normalize request path for stable endpoint assertions.

    FastAPI runs with root_path='/api', but callers can still send '/api/...'.
    We strip that prefix so traces align to documented endpoint paths.
    """
    path = (path or "").strip() or "/"
    if path == "/api":
        return "/"
    if path.startswith("/api/"):
        path = path[4:]
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


class E2ETraceStore:
    """Bounded in-memory request trace store keyed by run_id."""

    def __init__(self, max_runs: int, max_events_per_run: int):
        self._max_runs = max(1, max_runs)
        self._max_events_per_run = max(1, max_events_per_run)
        self._events: "OrderedDict[str, Deque[Dict[str, Any]]]" = OrderedDict()
        self._lock = RLock()

    def record(
        self,
        run_id: str,
        *,
        method: str,
        path: str,
        query: Dict[str, str],
        status_code: int,
        duration_ms: float,
        request_id: Optional[str],
    ) -> None:
        run_id = (run_id or "").strip()
        if not run_id:
            return

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "method": method.upper(),
            "path": normalize_path(path),
            "query": dict(query),
            "status_code": int(status_code),
            "duration_ms": round(float(duration_ms), 2),
            "request_id": request_id,
        }

        with self._lock:
            queue = self._events.get(run_id)
            if queue is None:
                queue = deque(maxlen=self._max_events_per_run)
                self._events[run_id] = queue
            else:
                self._events.move_to_end(run_id)

            queue.append(event)

            while len(self._events) > self._max_runs:
                self._events.popitem(last=False)

    def list(self, run_id: str) -> List[Dict[str, Any]]:
        run_id = (run_id or "").strip()
        if not run_id:
            return []
        with self._lock:
            queue = self._events.get(run_id)
            if queue is None:
                return []
            return list(queue)

    def clear(self, run_id: str) -> int:
        run_id = (run_id or "").strip()
        if not run_id:
            return 0
        with self._lock:
            queue = self._events.pop(run_id, None)
            return len(queue or ())

    def stats(self) -> Dict[str, int]:
        with self._lock:
            total_events = sum(len(queue) for queue in self._events.values())
            return {
                "tracked_runs": len(self._events),
                "total_events": total_events,
                "max_runs": self._max_runs,
                "max_events_per_run": self._max_events_per_run,
            }
