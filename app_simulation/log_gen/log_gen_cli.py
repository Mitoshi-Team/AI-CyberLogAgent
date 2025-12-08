"""CLI для управления генератором логов.

Предоставляет команды для запуска генератора в различных режимах:
- imitate: имитация реального сервера с генерацией 1 лог/сек
- record_logs_for_tests: быстрая генерация файла для тестирования

Использование:
    python -m app_simulation.log_gen.log_gen_cli start imitate attack
    python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable 1000
    python -m app_simulation.log_gen.log_gen_cli stop  # Ctrl+C для остановки в режиме imitate
"""

import argparse
import signal
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from .config_loader import ConfigLoader
from .log_gen import LogGenerator


# ANSI color codes для цветного вывода
class Colors:
    """ANSI коды цветов для терминала."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"


# Получаем директорию текущего файла
CURRENT_DIR = Path(__file__).parent

# Маппинг типов конфигураций на файлы (относительно текущей директории)
CONFIG_MAP = {
    "attack": CURRENT_DIR / "configs" / "attack.json",
    "realistic": CURRENT_DIR / "configs" / "realistic_mixed.json",
    "stable": CURRENT_DIR / "configs" / "stable.json",
    "load": CURRENT_DIR / "configs" / "high_load.json",
}

# Путь к выходному файлу логов (в текущей директории)
OUTPUT_LOG_FILE = CURRENT_DIR / "logs.log"


class LogGeneratorCLI:
    """Класс для управления генерацией логов через CLI."""

    def __init__(self) -> None:
        """Инициализация CLI менеджера."""
        self.running = True
        self.logs_generated = 0
        self.start_time = datetime.now()
        
        # Регистрация обработчиков сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> NoReturn:
        """Обработчик сигналов для graceful shutdown.

        Args:
            signum: Номер сигнала
            frame: Фрейм выполнения

        """
        print(f"\n\n{Colors.YELLOW}🛑 Получен сигнал остановки...{Colors.RESET}")
        self.running = False
        self._show_final_statistics()
        sys.exit(0)

    def _show_final_statistics(self) -> None:
        """Показывает финальную статистику генерации."""
        duration = datetime.now() - self.start_time
        print(f"\n{Colors.CYAN}📊 Статистика генерации:{Colors.RESET}")
        print(f"  {Colors.BOLD}Сгенерировано логов:{Colors.RESET} {self.logs_generated}")
        print(f"  {Colors.BOLD}Время работы:{Colors.RESET} {duration}")
        print(f"  {Colors.BOLD}Файл:{Colors.RESET} {OUTPUT_LOG_FILE.absolute()}")

    def _validate_config_path(self, config_type: str) -> Path:
        """Проверяет существование конфигурационного файла.

        Args:
            config_type: Тип конфигурации (attack, realistic, stable, load)

        Returns:
            Path объект конфигурационного файла

        Raises:
            FileNotFoundError: Если конфиг не найден

        """
        config_path = CONFIG_MAP[config_type]  # Уже Path объект
        if not config_path.exists():
            raise FileNotFoundError(
                f"Конфигурационный файл не найден: {config_path.absolute()}"
            )
        return config_path

    def _print_progress_bar(
        self, current: int, total: int, bar_length: int = 50
    ) -> None:
        """Отрисовывает прогресс-бар в терминале.

        Args:
            current: Текущее значение прогресса
            total: Максимальное значение
            bar_length: Длина прогресс-бара в символах

        """
        percent = current / total
        filled = int(bar_length * percent)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(
            f"\r{Colors.CYAN}Прогресс:{Colors.RESET} |{bar}| "
            f"{current}/{total} ({percent*100:.1f}%)",
            end="",
            flush=True,
        )

    def start_imitate_mode(self, config_type: str) -> None:
        """Запускает режим имитации реального сервера.

        Генерирует логи со скоростью 1 лог/секунду с реальными timestamp
        до получения сигнала остановки (Ctrl+C).

        Args:
            config_type: Тип конфигурации для генерации

        """
        config_path = self._validate_config_path(config_type)
        
        print(f"{Colors.GREEN}{Colors.BOLD}🚀 Запуск режима имитации{Colors.RESET}")
        print(f"  {Colors.BOLD}Конфигурация:{Colors.RESET} {config_type}")
        print(f"  {Colors.BOLD}Config файл:{Colors.RESET} {config_path}")
        print(f"  {Colors.BOLD}Скорость:{Colors.RESET} 1 лог/секунду")
        print(f"  {Colors.BOLD}Выходной файл:{Colors.RESET} {OUTPUT_LOG_FILE.absolute()}")
        print(f"\n{Colors.YELLOW}Нажмите Ctrl+C для остановки{Colors.RESET}\n")

        # Загружаем конфигурацию
        config = ConfigLoader.load_from_json(str(config_path))
        
        # Создаём/очищаем выходной файл
        OUTPUT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_LOG_FILE.open("w", encoding="utf-8") as f:
            f.write(f"# Log generation started: {datetime.now()}\n")
            f.write("# Mode: imitate\n")
            f.write(f"# Config: {config_type}\n\n")

        # Генерация логов в реальном времени
        log_count = 0
        while self.running:
            # Обновляем время в конфиге на текущее
            config.start_time = datetime.now()
            config.log_count = 1  # Генерируем по 1 логу
            
            # Создаём генератор и генерируем один лог
            generator = LogGenerator(config)
            generator.generate_logs()
            
            if generator.logs:
                log_entry = generator.logs[0]
                log_line = log_entry.format()
                
                # Записываем в файл
                with OUTPUT_LOG_FILE.open("a", encoding="utf-8") as f:
                    f.write(log_line + "\n")
                
                log_count += 1
                self.logs_generated = log_count
                
                # Выводим лог в консоль с цветом
                level_color = Colors.GREEN
                if "error" in log_line.lower() or "crit" in log_line.lower():
                    level_color = Colors.RED
                elif "warn" in log_line.lower():
                    level_color = Colors.YELLOW
                
                print(f"{level_color}[{log_count:05d}]{Colors.RESET} {log_line}")
            
            # Ждём 1 секунду перед следующим логом
            time.sleep(1)

    def start_record_mode(self, config_type: str, num_logs: int = 500) -> None:
        """Запускает режим быстрой записи логов для тестирования.

        Args:
            config_type: Тип конфигурации для генерации
            num_logs: Количество логов для генерации

        """
        config_path = self._validate_config_path(config_type)
        
        print(f"{Colors.GREEN}{Colors.BOLD}📝 Режим записи логов для тестирования{Colors.RESET}")
        print(f"  {Colors.BOLD}Конфигурация:{Colors.RESET} {config_type}")
        print(f"  {Colors.BOLD}Config файл:{Colors.RESET} {config_path}")
        print(f"  {Colors.BOLD}Количество логов:{Colors.RESET} {num_logs}")
        print(f"  {Colors.BOLD}Выходной файл:{Colors.RESET} {OUTPUT_LOG_FILE.absolute()}")
        print()

        # Загружаем конфигурацию
        config = ConfigLoader.load_from_json(str(config_path))
        config.log_count = num_logs
        
        # Создаём генератор
        generator = LogGenerator(config)
        
        # Генерация с прогресс-баром
        print(f"{Colors.CYAN}🔄 Генерация логов...{Colors.RESET}\n")
        
        # Генерируем логи порциями для отображения прогресса
        batch_size = max(1, num_logs // 100)  # 1% за раз
        generated = 0
        
        OUTPUT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT_LOG_FILE.open("w", encoding="utf-8") as f:
            f.write(f"# Log generation started: {datetime.now()}\n")
            f.write("# Mode: record_logs_for_tests\n")
            f.write(f"# Config: {config_type}\n")
            f.write(f"# Total logs: {num_logs}\n\n")
            
            while generated < num_logs:
                current_batch = min(batch_size, num_logs - generated)
                config.log_count = current_batch
                
                batch_generator = LogGenerator(config)
                batch_generator.generate_logs()
                
                # Записываем логи
                for log_entry in batch_generator.logs:
                    f.write(log_entry.format() + "\n")
                
                generator.logs.extend(batch_generator.logs)
                generated += len(batch_generator.logs)
                
                # Обновляем прогресс-бар
                self._print_progress_bar(generated, num_logs)
        
        print()  # Новая строка после прогресс-бара
        self.logs_generated = generated
        
        # Показываем статистику
        self._show_statistics(generator, config_type)
        
        print(f"\n{Colors.GREEN}✅ Логи успешно сгенерированы!{Colors.RESET}")
        print(f"💾 Сохранено в: {Colors.CYAN}{OUTPUT_LOG_FILE.absolute()}{Colors.RESET}\n")

    def _show_statistics(self, generator: LogGenerator, config_type: str) -> None:
        """Показывает детальную статистику по сгенерированным логам.

        Args:
            generator: Генератор с созданными логами
            config_type: Тип использованной конфигурации

        """
        duration = datetime.now() - self.start_time
        level_counts = Counter(log.level for log in generator.logs)
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}📊 Статистика генерации:{Colors.RESET}")
        print(f"  {Colors.BOLD}Конфигурация:{Colors.RESET} {config_type}")
        print(f"  {Colors.BOLD}Всего записей:{Colors.RESET} {len(generator.logs)}")
        print(f"  {Colors.BOLD}Время генерации:{Colors.RESET} {duration}")
        
        if generator.logs:
            print(
                f"  {Colors.BOLD}Период логов:{Colors.RESET} "
                f"{generator.logs[0].timestamp} - {generator.logs[-1].timestamp}"
            )
            log_duration = generator.logs[-1].timestamp - generator.logs[0].timestamp
            print(f"  {Colors.BOLD}Длительность логов:{Colors.RESET} {log_duration}")
        
        print(f"\n  {Colors.BOLD}Распределение по уровням:{Colors.RESET}")
        for level, count in sorted(
            level_counts.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / len(generator.logs)) * 100
            
            # Цвет в зависимости от уровня
            level_color = Colors.GREEN
            if level.value in ["error", "crit"]:
                level_color = Colors.RED
            elif level.value == "warn":
                level_color = Colors.YELLOW
            
            print(
                f"    {level_color}{level.value:8s}{Colors.RESET}: "
                f"{count:5d} ({percentage:5.1f}%)"
            )


def create_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки.

    Returns:
        Настроенный ArgumentParser

    """
    parser = argparse.ArgumentParser(
        description="Генератор логов - управление режимами генерации",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Режим имитации реального сервера (1 лог/сек, бесконечно)
  python -m app_simulation.log_gen.log_gen_cli start imitate attack
  python -m app_simulation.log_gen.log_gen_cli start imitate realistic
  
  # Режим записи для тестирования (быстрая генерация)
  python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable
  python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests load 1000
  
  # Остановка: Ctrl+C в режиме imitate

Доступные типы конфигураций:
  - attack      : Симуляция атаки на сервер
  - realistic   : Реалистичная смесь всех типов логов
  - stable      : Стабильная работа с минимумом ошибок
  - load        : Высокая нагрузка на сервер
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Команда для выполнения")

    # Команда start
    start_parser = subparsers.add_parser(
        "start", help="Запустить генератор логов"
    )
    start_parser.add_argument(
        "mode",
        choices=["imitate", "record_logs_for_tests"],
        help="Режим работы генератора",
    )
    start_parser.add_argument(
        "type",
        choices=["attack", "realistic", "stable", "load"],
        help="Тип конфигурации для генерации",
    )
    start_parser.add_argument(
        "num_logs",
        type=int,
        nargs="?",
        default=500,
        help="Количество логов (только для record_logs_for_tests, по умолчанию: 500)",
    )

    # Команда stop (информационная, реальная остановка через Ctrl+C)
    subparsers.add_parser(
        "stop", help="Остановить генератор (используйте Ctrl+C)"
    )

    return parser


def main() -> None:
    """Главная функция CLI."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if not args.command:
            parser.print_help()
            sys.exit(1)

        if args.command == "stop":
            print(
                f"{Colors.YELLOW}ℹ️  Для остановки генератора в режиме 'imitate' "
                f"используйте Ctrl+C{Colors.RESET}"
            )
            sys.exit(0)

        if args.command == "start":
            cli = LogGeneratorCLI()
            
            if args.mode == "imitate":
                # Режим имитации (num_logs игнорируется)
                cli.start_imitate_mode(args.type)
            
            elif args.mode == "record_logs_for_tests":
                # Режим записи для тестов
                cli.start_record_mode(args.type, args.num_logs)

    except FileNotFoundError as error:
        print(f"\n{Colors.RED}❌ Ошибка:{Colors.RESET} {error}", file=sys.stderr)
        sys.exit(1)
    
    except KeyboardInterrupt:
        # Обработано в signal_handler
        pass
    
    except Exception as error:
        print(
            f"\n{Colors.RED}❌ Неожиданная ошибка:{Colors.RESET} {error}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
