from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nats.aio.client import Client as NATS


MessageCallback = Callable[[bytes], Awaitable[None]]


class NATSGateway:
    """Thin async adapter around NATS."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: NATS | None = None

    async def connect(self) -> None:
        import nats

        self._client = await nats.connect(self._url)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.drain()
            await self._client.close()

    async def publish_json(self, subject: str, payload: dict[str, Any]) -> None:
        client = self._require_client()
        await client.publish(subject, json.dumps(payload).encode("utf-8"))
        await client.flush()

    async def subscribe(self, subject: str, callback: MessageCallback) -> None:
        client = self._require_client()

        async def handler(message: Any) -> None:
            await callback(message.data)

        await client.subscribe(subject, cb=handler)

    async def request_json(
        self,
        subject: str,
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        client = self._require_client()
        response = await client.request(
            subject,
            json.dumps(payload).encode("utf-8"),
            timeout=timeout_seconds,
        )
        return json.loads(response.data.decode("utf-8"))

    def _require_client(self) -> NATS:
        if self._client is None:
            raise RuntimeError("NATS gateway is not connected")
        return self._client


class FakeNATSGateway:
    """Test double for unit tests without external infrastructure."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []
        self.subscribers: dict[str, MessageCallback] = {}
        self.fail_next_publish = False

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def publish_json(self, subject: str, payload: dict[str, Any]) -> None:
        if self.fail_next_publish:
            self.fail_next_publish = False
            raise TimeoutError("simulated publish failure")
        self.published.append((subject, payload))

    async def subscribe(self, subject: str, callback: MessageCallback) -> None:
        self.subscribers[subject] = callback

    async def emit_result(self, payload: dict[str, Any]) -> None:
        callback = self.subscribers["supply.results"]
        await callback(json.dumps(payload).encode("utf-8"))
        await asyncio.sleep(0)
