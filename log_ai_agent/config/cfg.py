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
print(GIGACHAT_API_KEY)
