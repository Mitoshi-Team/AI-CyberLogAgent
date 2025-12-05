"""CLI интерфейс для генератора логов.

Предоставляет удобный интерфейс командной строки для генерации логов
с различными параметрами.
"""

import argparse
import sys
from pathlib import Path

from log_gen import ConfigLoader, GeneratorConfig, IncidentType, LogGenerator


def create_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки.

    Returns:
        Настроенный ArgumentParser

    """
    parser = argparse.ArgumentParser(
        description="Генератор реалистичных Apache/mod_jk логов с инцидентами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Генерация 100 логов с настройками по умолчанию
  python cli.py -o logs/output.log

  # Генерация с настройками
  python cli.py -o logs/output.log -n 500 -e 0.2 -i 0.1

  # Использование конфигурационного файла
  python cli.py -o logs/output.log -c config.json

  # Создание шаблона конфигурации
  python cli.py --create-config my_config.json

  # Генерация только инцидентов определённого типа
  python cli.py -o incidents.log -n 50 --incident-only worker_error
        """,
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Путь к выходному .log файлу",
    )

    parser.add_argument(
        "-n",
        "--log-count",
        type=int,
        default=100,
        help="Количество логов для генерации (по умолчанию: 100)",
    )

    parser.add_argument(
        "-e",
        "--error-probability",
        type=float,
        default=0.15,
        help="Вероятность ошибки от 0.0 до 1.0 (по умолчанию: 0.15)",
    )

    parser.add_argument(
        "-i",
        "--incident-probability",
        type=float,
        default=0.05,
        help="Вероятность инцидента от 0.0 до 1.0 (по умолчанию: 0.05)",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Путь к JSON файлу конфигурации",
    )

    parser.add_argument(
        "--create-config",
        type=str,
        metavar="FILEPATH",
        help="Создать шаблон конфигурационного файла и выйти",
    )

    parser.add_argument(
        "--incident-only",
        type=str,
        choices=[inc.value for inc in IncidentType],
        help="Генерировать только инциденты указанного типа",
    )

    parser.add_argument(
        "--time-range",
        type=int,
        nargs=2,
        metavar=("MIN", "MAX"),
        default=[1, 30],
        help="Диапазон секунд между логами (по умолчанию: 1 30)",
    )

    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Показать статистику по сгенерированным логам",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Предпросмотр логов без сохранения в файл",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Валидирует аргументы командной строки.

    Args:
        args: Аргументы командной строки

    Raises:
        ValueError: Если аргументы некорректны

    """
    if args.error_probability < 0 or args.error_probability > 1:
        raise ValueError("error_probability должна быть от 0.0 до 1.0")

    if args.incident_probability < 0 or args.incident_probability > 1:
        raise ValueError("incident_probability должна быть от 0.0 до 1.0")

    if args.log_count < 1:
        raise ValueError("log_count должна быть больше 0")

    if args.time_range[0] < 0 or args.time_range[1] < args.time_range[0]:
        raise ValueError("Некорректный диапазон времени")


def generate_logs(args: argparse.Namespace) -> None:
    """Генерирует логи на основе аргументов командной строки.

    Args:
        args: Аргументы командной строки

    """
    # Загружаем конфигурацию
    if args.config:
        print(f"📝 Загрузка конфигурации из {args.config}...")
        config = ConfigLoader.load_from_json(args.config)
    else:
        # Создаём конфигурацию из аргументов CLI
        config = GeneratorConfig(
            log_count=args.log_count,
            error_probability=args.error_probability,
            incident_probability=args.incident_probability,
            time_increment_seconds=tuple(args.time_range),
        )

    # Создаём генератор
    generator = LogGenerator(config)

    print(f"🔄 Генерация {args.log_count} логов...")

    # Генерируем логи
    if args.incident_only:
        # Генерируем только инциденты
        incident_type = IncidentType(args.incident_only)
        for _ in range(args.log_count):
            incident_logs = generator.generate_incident(incident_type)
            generator.logs.extend(incident_logs)
    else:
        # Обычная генерация
        generator.generate_logs()

    print(f"✓ Сгенерировано {len(generator.logs)} записей")

    # Показываем статистику
    if args.show_stats or args.preview:
        show_statistics(generator)

    # Предпросмотр
    if args.preview:
        print("\n📄 Предпросмотр логов (первые 20 записей):\n")
        for log in generator.logs[:20]:
            print(log.format())
        if len(generator.logs) > 20:
            print(f"\n... ещё {len(generator.logs) - 20} записей")

    # Сохраняем в файл
    if args.output:
        output_path = Path(args.output)
        generator.save_to_file(output_path)
        print(f"💾 Логи сохранены в: {output_path.absolute()}")
    elif not args.preview:
        print("\n⚠️  Файл не сохранён. Используйте -o для указания выходного файла")


def show_statistics(generator: LogGenerator) -> None:
    """Показывает статистику по сгенерированным логам.

    Args:
        generator: Генератор с созданными логами

    """
    from collections import Counter

    # Подсчитываем статистику
    level_counts = Counter(log.level for log in generator.logs)

    print("\n📊 Статистика:")
    print(f"  Всего записей: {len(generator.logs)}")

    if generator.logs:
        print(
            f"  Период: {generator.logs[0].timestamp} - {generator.logs[-1].timestamp}"
        )
        duration = generator.logs[-1].timestamp - generator.logs[0].timestamp
        print(f"  Длительность: {duration}")

    print("\n  Распределение по уровням:")
    for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(generator.logs)) * 100
        print(f"    {level.value:8s}: {count:5d} ({percentage:5.1f}%)")


def main() -> None:
    """Главная функция CLI."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Создание конфигурации
        if args.create_config:
            ConfigLoader.create_default_config(args.create_config)
            print(
                f"\n📝 Теперь вы можете отредактировать конфигурацию "
                f"и использовать её:\n"
                f"   python cli.py -c {args.create_config} -o output.log"
            )
            return

        # Проверяем, что указан выходной файл или режим предпросмотра
        if not args.output and not args.preview:
            parser.error("Требуется указать -o/--output или использовать --preview")

        # Валидируем аргументы
        validate_args(args)

        # Генерируем логи
        generate_logs(args)

        print("\n✅ Готово!")

    except Exception as error:
        print(f"\n❌ Ошибка: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
