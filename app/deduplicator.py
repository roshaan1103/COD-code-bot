import time
from collections import OrderedDict
from threading import Lock


# A detected code remains in the cache for 5 minutes.
CACHE_TTL_SECONDS = 5 * 60

# Safety limit so the cache can never grow indefinitely.
MAX_CACHE_SIZE = 1000


class CodeDeduplicator:
    """
    Prevents the same giveaway code from being processed repeatedly.

    Each code remains in the cache for CACHE_TTL_SECONDS after
    its first detection.

    The cache is also bounded by MAX_CACHE_SIZE.
    """

    def __init__(
        self,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        max_size: int = MAX_CACHE_SIZE,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

        # code -> detection timestamp
        self._cache = OrderedDict()

        # Protect the cache if multiple threads access it later.
        self._lock = Lock()

    def is_duplicate(self, code: str) -> bool:
        """
        Check whether a code has already been detected recently.

        Returns:
            True  -> duplicate
            False -> new code

        A new code is automatically stored.
        """

        now = time.monotonic()

        with self._lock:

            detected_at = self._cache.get(code)

            # Code exists in the cache.
            if detected_at is not None:

                # Still inside the TTL.
                if now - detected_at < self.ttl_seconds:
                    return True

                # TTL expired.
                del self._cache[code]

            # New code.
            self._cache[code] = now

            # Keep cache bounded.
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

            return False

    def size(self) -> int:
        """
        Return the number of entries currently stored.
        """

        with self._lock:
            return len(self._cache)