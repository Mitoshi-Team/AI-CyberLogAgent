#!/usr/bin/env python3
"""Загрузка полной базы MITRE ATT&CK с GitHub в локальный STIX файл."""

import json
import sys
from pathlib import Path

import requests


def download_mitre_from_github(output_path: Path):
    """Загрузить MITRE ATT&CK Enterprise с GitHub и сохранить в файл."""
    # Прямая ссылка на актуальную версию MITRE ATT&CK Enterprise
    url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

    print("Загрузка MITRE ATT&CK с GitHub...")
    print(f"URL: {url}")

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    attack_data = response.json()

    # Сохранение в файл
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(attack_data, f, ensure_ascii=False, indent=2)

    obj_count = len(attack_data.get("objects", []))
    print(f"✓ Загружено и сохранено {obj_count} объектов")
    print(f"  Путь: {output_path}")

    return attack_data


if __name__ == "__main__":
    output = Path(__file__).parent / "mitre_data" / "enterprise-attack.json"
    try:
        download_mitre_from_github(output)
        print("\n✓ Данные MITRE ATT&CK готовы к использованию")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
