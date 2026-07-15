#!/usr/bin/env python3
"""Retry con backoff esponenziale per chiamate API transienti."""

from __future__ import annotations

import os
import random
import sys
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

RETRY_MAX_ATTEMPTS = int(os.environ.get("API_RETRY_MAX_ATTEMPTS", "6"))
RETRY_BASE_DELAY = float(os.environ.get("API_RETRY_BASE_DELAY", "5"))
RETRY_MAX_DELAY = float(os.environ.get("API_RETRY_MAX_DELAY", "120"))

GEMINI_MAX_CALLS_PER_MINUTE = int(os.environ.get("GEMINI_MAX_CALLS_PER_MINUTE", "5"))
GEMINI_RATE_WINDOW_SECONDS = float(os.environ.get("GEMINI_RATE_WINDOW_SECONDS", "60"))
GEMINI_MIN_PAUSE_SECONDS = float(
    os.environ.get("GEMINI_MIN_PAUSE_SECONDS", str(GEMINI_RATE_WINDOW_SECONDS))
)
GEMINI_RETRY_BASE_DELAY = float(
    os.environ.get("GEMINI_RETRY_BASE_DELAY", str(GEMINI_MIN_PAUSE_SECONDS))
)
GEMINI_RETRY_MAX_DELAY = float(os.environ.get("GEMINI_RETRY_MAX_DELAY", "180"))

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


class MinuteRateLimiter:
    """Limita le chiamate API in una finestra mobile; pausa >= window al raggiungimento del limite."""

    def __init__(
        self,
        *,
        max_calls: int = GEMINI_MAX_CALLS_PER_MINUTE,
        window_seconds: float = GEMINI_RATE_WINDOW_SECONDS,
        label: str = "Gemini rate limit",
    ) -> None:
        if max_calls < 1:
            raise ValueError("max_calls deve essere >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds deve essere > 0")
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.label = label
        self._timestamps: list[float] = []

    def acquire(self) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) >= self.max_calls:
            wait_s = self.window_seconds
            print(
                f"\n[{self.label}] Raggiunto il limite di {self.max_calls} "
                f"chiamate per minuto. Attendo {wait_s:.0f}s...\n",
                file=sys.stderr,
            )
            time.sleep(wait_s)
            self._timestamps.clear()

        self._timestamps.append(time.monotonic())


def _status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value

    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value

    return None


def is_retryable_error(exc: BaseException) -> bool:
    is_retryable = getattr(exc, "is_retryable", None)
    if is_retryable is True:
        return True
    if is_retryable is False:
        return False

    status = _status_code(exc)
    if status in RETRYABLE_STATUS_CODES:
        return True

    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    name = exc.__class__.__name__.lower()
    if any(token in name for token in ("timeout", "connection", "unavailable", "ratelimit")):
        return True

    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "503",
            "429",
            "502",
            "504",
            "500",
            "unavailable",
            "high demand",
            "rate limit",
            "temporarily",
            "timeout",
            "connection",
            "overloaded",
        )
    )


def retry_delay(
    attempt: int,
    *,
    base_delay: float,
    max_delay: float,
    min_delay: float | None = None,
    fixed_delay: float | None = None,
) -> float:
    if fixed_delay is not None:
        return fixed_delay

    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
    if min_delay is not None:
        delay = max(delay, min_delay)
    jitter = random.uniform(0, delay * 0.25)
    return delay + jitter


def call_with_retry(
    fn: Callable[[], T],
    *,
    label: str = "API",
    max_attempts: int = RETRY_MAX_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    min_delay: float | None = None,
    fixed_delay: float | None = None,
) -> T:
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts or not is_retryable_error(exc):
                raise

            wait_s = retry_delay(
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                min_delay=min_delay,
                fixed_delay=fixed_delay,
            )
            status = _status_code(exc)
            status_txt = f" HTTP {status}" if status else ""
            print(
                f"\n[{label}] Tentativo {attempt}/{max_attempts} fallito{status_txt}: {exc}",
                file=sys.stderr,
            )
            print(
                f"[{label}] Attendo {wait_s:.1f}s prima del prossimo tentativo...",
                file=sys.stderr,
            )
            time.sleep(wait_s)

    assert last_exc is not None
    raise last_exc
