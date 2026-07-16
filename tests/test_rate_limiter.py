"""Tests for modules/rate_limiter.py."""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.rate_limiter import RateLimiter


class TestRateLimiterDisabled:
    """RateLimiter with rate=0 or rate=None is a no-op."""

    def test_zero_rate_is_noop(self):
        rl = RateLimiter(rate=0, burst=0)
        assert not rl._enabled
        # acquire should return instantly without sleeping
        start = time.monotonic()
        for _ in range(100):
            rl.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1, f"No-op limiter took {elapsed:.3f}s for 100 calls"

    def test_none_rate_is_noop(self):
        rl = RateLimiter(rate=None, burst=None)
        assert not rl._enabled
        start = time.monotonic()
        rl.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.05


class TestRateLimiterEnabled:
    """RateLimiter with a finite rate actually throttles."""

    def test_burst_allows_immediate_calls(self):
        """burst=5 means 5 calls should complete without sleeping."""
        rl = RateLimiter(rate=1, burst=5)
        start = time.monotonic()
        for _ in range(5):
            rl.acquire()
        elapsed = time.monotonic() - start
        # Should be very fast since tokens are pre-filled
        assert elapsed < 0.5, f"Burst calls took {elapsed:.3f}s"

    def test_throttle_after_burst_exhausted(self):
        """After the burst is consumed calls should be throttled to ~rate/s."""
        rl = RateLimiter(rate=10, burst=1)
        # Consume the single burst token immediately
        rl.acquire()
        # Next call must wait roughly 1/rate = 0.1s
        start = time.monotonic()
        rl.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05, f"Expected throttle but elapsed only {elapsed:.3f}s"
        assert elapsed < 1.0, f"Throttle took too long: {elapsed:.3f}s"

    def test_thread_safety(self):
        """Multiple threads can call acquire() concurrently without errors."""
        import threading

        rl = RateLimiter(rate=100, burst=200)
        errors = []

        def worker():
            try:
                for _ in range(10):
                    rl.acquire()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread errors: {errors}"

    def test_enabled_flag(self):
        rl = RateLimiter(rate=5, burst=10)
        assert rl._enabled

    def test_burst_defaults_to_rate_when_none(self):
        rl = RateLimiter(rate=7, burst=None)
        assert rl._burst == 7.0
