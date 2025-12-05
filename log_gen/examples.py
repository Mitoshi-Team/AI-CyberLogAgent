"""Примеры использования генератора логов.

Демонстрирует различные способы генерации логов и инцидентов.
"""

from datetime import datetime, timedelta
from pathlib import Path

from log_gen import (
    GeneratorConfig,
    IncidentType,
    LogGenerator,
    LogLevel,
)


def example_basic_generation() -> None:
    """Базовая генерация логов с настройками по умолчанию."""
    print("=" * 60)
    print("ПРИМЕР 1: Базовая генерация")
    print("=" * 60)

    generator = LogGenerator()
    logs = generator.generate_logs()

    print(f"✓ Сгенерировано {len(logs)} логов")
    print("\nПервые 5 логов:")
    for log in logs[:5]:
        print(f"  {log.format()}")

    generator.save_to_file("examples/basic_logs.log")
    print("\n✓ Сохранено в examples/basic_logs.log\n")


def example_custom_config() -> None:
    """Генерация с кастомной конфигурацией."""
    print("=" * 60)
    print("ПРИМЕР 2: Кастомная конфигурация")
    print("=" * 60)

    # Создаём конфигурацию с большим количеством ошибок
    config = GeneratorConfig(
        log_count=50,
        error_probability=0.3,  # 30% ошибок
        incident_probability=0.15,  # 15% инцидентов
        time_increment_seconds=(2, 10),  # Более частые логи
    )

    generator = LogGenerator(config)
    logs = generator.generate_logs()

    # Подсчитываем статистику
    error_count = sum(1 for log in logs if log.level == LogLevel.ERROR)
    critical_count = sum(1 for log in logs if log.level == LogLevel.CRITICAL)

    print(f"✓ Сгенерировано {len(logs)} логов")
    print(f"  - Ошибок: {error_count}")
    print(f"  - Критических: {critical_count}")

    generator.save_to_file("examples/high_error_rate.log")
    print("\n✓ Сохранено в examples/high_error_rate.log\n")


def example_specific_incident() -> None:
    """Генерация специфичного инцидента."""
    print("=" * 60)
    print("ПРИМЕР 3: Генерация инцидента Memory Leak")
    print("=" * 60)

    generator = LogGenerator()

    # Генерируем несколько инцидентов с утечками памяти
    all_logs = []
    for i in range(3):
        incident_logs = generator.generate_incident(IncidentType.MEMORY_LEAK)
        all_logs.extend(incident_logs)
        print(f"✓ Инцидент {i + 1}: {len(incident_logs)} записей")

    # Сохраняем
    generator.logs = all_logs
    generator.save_to_file("examples/memory_leak_incidents.log")

    print(f"\n✓ Всего записей: {len(all_logs)}")
    print("✓ Сохранено в examples/memory_leak_incidents.log\n")


def example_mixed_incidents() -> None:
    """Генерация логов с различными типами инцидентов."""
    print("=" * 60)
    print("ПРИМЕР 4: Смешанные инциденты")
    print("=" * 60)

    generator = LogGenerator()

    # Генерируем по одному инциденту каждого типа
    for incident_type in IncidentType:
        incident_logs = generator.generate_incident(incident_type)
        generator.logs.extend(incident_logs)
        print(f"✓ {incident_type.value}: {len(incident_logs)} записей")

    # Сортируем по времени
    generator.logs.sort(key=lambda log: log.timestamp)

    print(f"\n✓ Всего записей: {len(generator.logs)}")
    generator.save_to_file("examples/all_incident_types.log")
    print("✓ Сохранено в examples/all_incident_types.log\n")


def example_time_series() -> None:
    """Генерация логов с временными сериями."""
    print("=" * 60)
    print("ПРИМЕР 5: Временная серия за 24 часа")
    print("=" * 60)

    # Начинаем со вчерашнего дня
    start_time = datetime.now() - timedelta(days=1)

    config = GeneratorConfig(
        start_time=start_time,
        log_count=200,  # ~8 логов в час
        time_increment_seconds=(300, 600),  # 5-10 минут
        error_probability=0.1,
        incident_probability=0.03,
    )

    generator = LogGenerator(config)
    logs = generator.generate_logs()

    print(f"✓ Сгенерировано {len(logs)} логов")
    print(f"  Начало: {logs[0].timestamp}")
    print(f"  Конец: {logs[-1].timestamp}")
    print(f"  Длительность: {logs[-1].timestamp - logs[0].timestamp}")

    generator.save_to_file("examples/24_hour_timeline.log")
    print("\n✓ Сохранено в examples/24_hour_timeline.log\n")


def example_security_audit() -> None:
    """Генерация логов для симуляции аудита безопасности."""
    print("=" * 60)
    print("ПРИМЕР 6: Аудит безопасности")
    print("=" * 60)

    generator = LogGenerator()

    # Инциденты безопасности
    security_incidents = [
        IncidentType.AUTHENTICATION_FAILURE,
        IncidentType.PERMISSION_DENIED,
    ]

    print("Генерация инцидентов безопасности:")
    for incident_type in security_incidents:
        # Генерируем несколько инцидентов каждого типа
        for _ in range(3):
            incident_logs = generator.generate_incident(incident_type)
            generator.logs.extend(incident_logs)

        print(f"  ✓ {incident_type.value}")

    # Добавляем нормальные логи для контекста
    config = GeneratorConfig(log_count=50)
    temp_gen = LogGenerator(config)
    normal_logs = temp_gen.generate_logs()
    generator.logs.extend(normal_logs)

    # Сортируем по времени
    generator.logs.sort(key=lambda log: log.timestamp)

    print(f"\n✓ Всего записей: {len(generator.logs)}")
    generator.save_to_file("examples/security_audit.log")
    print("✓ Сохранено в examples/security_audit.log\n")


def main() -> None:
    """Запуск всех примеров."""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ГЕНЕРАТОРА ЛОГОВ AI-CyberLogAgent")
    print("=" * 60 + "\n")

    # Создаём директорию для примеров
    Path("examples").mkdir(exist_ok=True)

    # Запускаем примеры
    example_basic_generation()
    example_custom_config()
    example_specific_incident()
    example_mixed_incidents()
    example_time_series()
    example_security_audit()

    print("=" * 60)
    print("✅ Все примеры успешно выполнены!")
    print("=" * 60)
    print("\nСгенерированные файлы:")
    print("  - examples/basic_logs.log")
    print("  - examples/high_error_rate.log")
    print("  - examples/memory_leak_incidents.log")
    print("  - examples/all_incident_types.log")
    print("  - examples/24_hour_timeline.log")
    print("  - examples/security_audit.log")
    print()


if __name__ == "__main__":
    main()
