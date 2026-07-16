"""Token bucket rate limiter for outbound qBittorrent API and webhook calls."""

import threading
import time

from modules import util

logger = util.logger


class RateLimiter:
    """Thread-safe token bucket rate limiter.

    Args:
        rate: Maximum sustained requests per second. Pass 0 or None to disable
              rate limiting entirely (all acquire() calls become no-ops).
        burst: Maximum burst size (bucket capacity). Must be >= rate.
    """

    def __init__(self, rate, burst):
        if not rate:
            self._enabled = False
            return

        self._enabled = True
        self._rate = float(rate)
        self._burst = float(burst) if burst else float(rate)
        self._tokens = self._burst
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        """Block until a token is available.

        If the limiter is disabled this returns immediately without sleeping.
        Logs a debug message when it has to throttle (sleep > 0).
        """
        if not self._enabled:
            return

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            # Refill tokens based on elapsed time, capped at burst
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate)

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # Not enough tokens — calculate how long to wait
            wait = (1.0 - self._tokens) / self._rate
            self._tokens = 0.0

        logger.debug(f"Rate limiter throttling: sleeping {wait:.3f}s")
        time.sleep(wait)
