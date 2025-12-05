"""Загрузчик конфигурации для генератора логов.

Модуль предоставляет функции для загрузки конфигурации из YAML/JSON файлов
и валидации параметров.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from log_gen import GeneratorConfig, IncidentType, LogType


class ConfigLoader:
    """Класс для загрузки и валидации конфигурации генератора."""

    @staticmethod
    def load_from_json(filepath: Path | str) -> GeneratorConfig:
        """Загружает конфигурацию из JSON файла.

        Args:
            filepath: Путь к JSON файлу с конфигурацией

        Returns:
            Объект GeneratorConfig с загруженными параметрами

        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если формат файла некорректен

        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {filepath}")

        with filepath.open("r", encoding="utf-8") as file:
            config_data = json.load(file)

        return ConfigLoader._parse_config(config_data)

    @staticmethod
    def _parse_config(config_data: dict[str, Any]) -> GeneratorConfig:
        """Парсит словарь конфигурации и создаёт объект GeneratorConfig.

        Args:
            config_data: Словарь с параметрами конфигурации

        Returns:
            Объект GeneratorConfig

        """
        # Парсим временные параметры
        start_time = datetime.now()
        if "start_time" in config_data:
            start_time = datetime.fromisoformat(config_data["start_time"])

        # Парсим типы инцидентов
        incident_types = []
        if "incident_types" in config_data:
            incident_types = [
                IncidentType(inc_type) for inc_type in config_data["incident_types"]
            ]
        else:
            incident_types = list(IncidentType)

        # Парсим веса типов логов
        log_type_weights = {}
        if "log_type_weights" in config_data:
            log_type_weights = {
                LogType(log_type): weight
                for log_type, weight in config_data["log_type_weights"].items()
            }
        else:
            # Веса по умолчанию
            log_type_weights = {
                LogType.NORMAL: 0.4,
                LogType.ERROR: 0.1,
                LogType.MOD_JK_WORKER_INIT: 0.05,
                LogType.MOD_JK_WORKER_ERROR: 0.05,
                LogType.JK2_CHILD_INIT: 0.1,
                LogType.JK2_CHILD_ERROR: 0.05,
                LogType.CLIENT_DIRECTORY_FORBIDDEN: 0.1,
                LogType.CLIENT_FILE_NOT_FOUND: 0.1,
                LogType.SYSTEM_NOTICE: 0.05,
            }

        # Парсим диапазоны IP адресов
        client_ip_ranges = config_data.get(
            "client_ip_ranges",
            ["192.168.0.0/16", "10.0.0.0/8", "public"],
        )

        # Парсим запрещённые пути
        forbidden_paths = config_data.get(
            "forbidden_paths",
            [
                "/var/www/html/",
                "/var/www/html/admin/",
                "/var/www/html/images/",
                "/usr/local/apache/htdocs/",
            ],
        )

        # Создаём конфигурацию
        return GeneratorConfig(
            start_time=start_time,
            log_count=config_data.get("log_count", 100),
            time_increment_seconds=tuple(
                config_data.get("time_increment_seconds", [1, 30])
            ),
            process_id_range=tuple(config_data.get("process_id_range", [6000, 7000])),
            slot_range=tuple(config_data.get("slot_range", [1, 10])),
            error_probability=config_data.get("error_probability", 0.15),
            incident_probability=config_data.get("incident_probability", 0.05),
            incident_types=incident_types,
            incident_duration_logs=tuple(
                config_data.get("incident_duration_logs", [3, 10])
            ),
            log_type_weights=log_type_weights,
            client_ip_ranges=client_ip_ranges,
            forbidden_paths=forbidden_paths,
        )

    @staticmethod
    def create_default_config(filepath: Path | str) -> None:
        """Создаёт файл конфигурации по умолчанию.

        Args:
            filepath: Путь к файлу для сохранения конфигурации

        """
        filepath = Path(filepath)

        default_config = {
            "log_count": 100,
            "time_increment_seconds": [1, 30],
            "process_id_range": [6000, 7000],
            "slot_range": [1, 10],
            "error_probability": 0.15,
            "incident_probability": 0.05,
            "incident_duration_logs": [3, 10],
            "incident_types": [inc.value for inc in IncidentType],
            "log_type_weights": {
                "normal": 0.4,
                "error": 0.1,
                "mod_jk_worker_init": 0.05,
                "mod_jk_worker_error": 0.05,
                "jk2_child_init": 0.1,
                "jk2_child_error": 0.05,
                "client_directory_forbidden": 0.1,
                "client_file_not_found": 0.1,
                "system_notice": 0.05,
            },
            "client_ip_ranges": [
                "192.168.0.0/16",
                "10.0.0.0/8",
                "public",
            ],
            "forbidden_paths": [
                "/var/www/html/",
                "/var/www/html/admin/",
                "/var/www/html/images/",
                "/usr/local/apache/htdocs/",
            ],
            "_comment": "Конфигурация генератора Apache логов",
            "_log_type_weights_info": (
                "Веса определяют вероятность генерации каждого типа лога. "
                "Сумма весов должна быть 1.0"
            ),
            "_client_ip_ranges_info": (
                "Диапазоны IP адресов: 'public' для публичных IP, "
                "или CIDR нотация (192.168.0.0/16)"
            ),
            "_forbidden_paths_info": "Список путей для генерации ошибок доступа",
        }

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=2, ensure_ascii=False)

        print(f"✓ Создан файл конфигурации: {filepath.absolute()}")


def main() -> None:
    """Пример создания конфигурационного файла."""
    config_path = Path("log_generator_config.json")
    ConfigLoader.create_default_config(config_path)


if __name__ == "__main__":
    main()
