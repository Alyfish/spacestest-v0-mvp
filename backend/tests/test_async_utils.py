import asyncio

import pytest

from async_utils import TTLCache, get_or_compute


def test_get_or_compute_failure_clears_in_flight_and_allows_retry():
    async def _scenario():
        in_flight = {}
        cache = TTLCache()
        key = "unit:test:get_or_compute"
        calls = {"count": 0}

        async def fail_once():
            calls["count"] += 1
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await get_or_compute(
                in_flight=in_flight,
                cache=cache,
                key=key,
                compute_fn=fail_once,
                ttl=60,
            )

        assert key not in in_flight

        async def succeed():
            calls["count"] += 1
            return {"ok": True}

        result = await get_or_compute(
            in_flight=in_flight,
            cache=cache,
            key=key,
            compute_fn=succeed,
            ttl=60,
        )

        assert result == {"ok": True}
        assert calls["count"] == 2
        assert key not in in_flight

    asyncio.run(_scenario())
