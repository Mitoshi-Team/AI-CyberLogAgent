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
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 2.0,
        dlq_enabled: bool = True,
        dlq_topic: str | None = None,
        payload_handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        self.enabled = enabled
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.output_file = Path(output_file)
        self.retry_attempts = max(1, int(retry_attempts))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self.dlq_enabled = dlq_enabled
        self.dlq_topic = dlq_topic
        self.payload_handler = payload_handler

        self._consumer: Any | None = None
        self._producer: Any | None = None
        self._topic_partition_cls: Any | None = None
        self._offset_metadata_cls: Any | None = None
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
            AIOKafkaProducer = aiokafka_module.AIOKafkaProducer
            aiokafka_structs = importlib.import_module("aiokafka.structs")
            self._topic_partition_cls = aiokafka_structs.TopicPartition
            self._offset_metadata_cls = aiokafka_structs.OffsetAndMetadata
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
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )

        if self.dlq_enabled and self.dlq_topic:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            )
            await self._producer.start()

        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

        logger.info(
            "Kafka consumer started: topic=%s, bootstrap=%s, group=%s",
            self.topic,
            self.bootstrap_servers,
            self.group_id,
        )
        logger.info(
            "Kafka consumer mode: manual_commit=true, retry_attempts=%s, dlq_enabled=%s, dlq_topic=%s",
            self.retry_attempts,
            self.dlq_enabled,
            self.dlq_topic,
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

        if self._producer is not None:
            await self._producer.stop()

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
                        handled = await self._process_message_with_retry(
                            message, payload
                        )
                        if not handled:
                            raise RuntimeError(
                                "Kafka message processing failed and DLQ publish was unsuccessful"
                            )
                        await self._commit_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Kafka consume error: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _process_message_with_retry(
        self, message: Any, payload: dict[str, Any]
    ) -> bool:
        """Process one Kafka message with retries and optional DLQ fallback."""
        last_error: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                await self._persist_payload(payload)
                await self._handle_payload(payload)
                if attempt > 1:
                    logger.info(
                        "Kafka message processed after retry: topic=%s partition=%s offset=%s attempts=%s",
                        message.topic,
                        message.partition,
                        message.offset,
                        attempt,
                    )
                return True
            except Exception as exc:
                last_error = exc
                logger.error(
                    "Kafka message processing failed: topic=%s partition=%s offset=%s attempt=%s/%s error=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                    attempt,
                    self.retry_attempts,
                    exc,
                    exc_info=True,
                )

                if attempt < self.retry_attempts and self.retry_backoff_seconds > 0:
                    backoff_seconds = self.retry_backoff_seconds * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_seconds)

        if not self.dlq_enabled:
            logger.error(
                "Kafka message permanently failed with DLQ disabled: topic=%s partition=%s offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )
            return False

        return await self._publish_to_dlq(message, payload, last_error)

    async def _publish_to_dlq(
        self,
        message: Any,
        payload: dict[str, Any],
        error: Exception | None,
    ) -> bool:
        """Publish permanently failed message to DLQ topic."""
        if self._producer is None or not self.dlq_topic:
            logger.error(
                "DLQ producer is unavailable: topic=%s partition=%s offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )
            return False

        dlq_message = {
            "failed_at": datetime.now(UTC).isoformat(),
            "source_topic": message.topic,
            "source_partition": message.partition,
            "source_offset": message.offset,
            "error": str(error) if error else "unknown error",
            "retry_attempts": self.retry_attempts,
            "payload": payload,
        }

        try:
            await self._producer.send_and_wait(self.dlq_topic, dlq_message)
            logger.warning(
                "Message moved to DLQ: dlq_topic=%s source_topic=%s partition=%s offset=%s",
                self.dlq_topic,
                message.topic,
                message.partition,
                message.offset,
            )
            return True
        except Exception as exc:
            logger.error(
                "Failed to publish message to DLQ: dlq_topic=%s source_topic=%s partition=%s offset=%s error=%s",
                self.dlq_topic,
                message.topic,
                message.partition,
                message.offset,
                exc,
                exc_info=True,
            )
            return False

    async def _commit_message(self, message: Any) -> None:
        """Commit only one successfully processed Kafka message."""
        if (
            self._consumer is None
            or self._offset_metadata_cls is None
            or self._topic_partition_cls is None
        ):
            return

        topic_partition = self._topic_partition_cls(message.topic, message.partition)
        offsets = {
            topic_partition: self._offset_metadata_cls(message.offset + 1, "processed")
        }
        await self._consumer.commit(offsets)

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
            raise
