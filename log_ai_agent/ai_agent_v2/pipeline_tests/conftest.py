"""Shared test configuration with .env loading."""

from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[OK] Loaded .env from: {env_path}")
else:
    print(f"[WARN] .env file not found at: {env_path}")
