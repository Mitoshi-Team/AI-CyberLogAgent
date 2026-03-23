import os
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # Skip empty lines and comments
                key, value = line.split("=", 1)
                os.environ[key] = value

GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


KAFKA_ENABLED = _get_bool_env("KAFKA_ENABLED", True)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "processed-logs-batches")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "cyberlog-backend-group")
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")

PIPELINE_EXTERNAL_LOGS_DIR = os.getenv(
    "PIPELINE_EXTERNAL_LOGS_DIR", "/app/shared/external"
)
PIPELINE_PROCESSED_LOGS_DIR = os.getenv(
    "PIPELINE_PROCESSED_LOGS_DIR", "/app/shared/processed"
)
PIPELINE_COLLECTED_LOGS_FILE = os.getenv(
    "PIPELINE_COLLECTED_LOGS_FILE", "/app/shared/processed/collected_logs.txt"
)
PIPELINE_CONSUMED_LOGS_FILE = os.getenv(
    "PIPELINE_CONSUMED_LOGS_FILE", "/app/shared/processed/kafka_consumed_logs.jsonl"
)
PIPELINE_KAFKA_AUTO_ANALYZE = _get_bool_env("PIPELINE_KAFKA_AUTO_ANALYZE", True)
