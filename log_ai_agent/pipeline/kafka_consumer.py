"""Kafka consumer for receiving log batches from Vector."""

import asyncio
import importlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class KafkaLogBatchConsumer:
    """Consumes Vector-produced log batches and stores them for backend processing."""

    def __init__(
        self,
        enabled: bool,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        auto_offset_reset: str,
        output_file: str,
        payload_handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        self.enabled = enabled
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.output_file = Path(output_file)
        self.payload_handler = payload_handler

        self._consumer: Any | None = None
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start background Kafka consumption."""
        if not self.enabled:
            logger.info("Kafka pipeline is disabled")
            return

        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            aiokafka_module = importlib.import_module("aiokafka")
            AIOKafkaConsumer = aiokafka_module.AIOKafkaConsumer
        except ModuleNotFoundError:
            logger.error(
                "aiokafka is not installed. Install dependencies before starting the backend pipeline."
            )
            return

        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )

        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

        logger.info(
            "Kafka consumer started: topic=%s, bootstrap=%s, group=%s",
            self.topic,
            self.bootstrap_servers,
            self.group_id,
        )

    async def stop(self) -> None:
        """Stop background Kafka consumption."""
        self._running = False

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._consumer is not None:
            await self._consumer.stop()

        logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        """Continuously poll Kafka and persist consumed batches."""
        if self._consumer is None:
            return

        while self._running:
            try:
                message_groups = await self._consumer.getmany(
                    timeout_ms=1000,
                    max_records=100,
                )

                for _, messages in message_groups.items():
                    for message in messages:
                        payload = message.value
                        await self._persist_payload(payload)
                        await self._handle_payload(payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Kafka consume error: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _persist_payload(self, payload: dict[str, Any]) -> None:
        """Append consumed payload as JSON lines for downstream usage."""
        record = {
            "received_at": datetime.now(UTC).isoformat(),
            "source": "kafka",
            "payload": payload,
        }

        with self.output_file.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def _handle_payload(self, payload: dict[str, Any]) -> None:
        """Process consumed payload with an optional callback."""
        if self.payload_handler is None:
            return

        try:
            await self.payload_handler(payload)
        except Exception as exc:
            logger.error("Kafka payload processing failed: %s", exc, exc_info=True)
