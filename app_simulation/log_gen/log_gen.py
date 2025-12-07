"""Генератор логов для симуляции Apache/mod_jk логов и инцидентов.

Модуль предоставляет гибкую систему генерации реалистичных логов веб-сервера
с возможностью создания нормальных событий и инцидентов безопасности.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    """Уровни логирования в Apache формате."""

    NOTICE = "notice"
    ERROR = "error"
    WARN = "warn"
    CRITICAL = "crit"
    INFO = "info"
    DEBUG = "debug"


class LogType(Enum):
    """Типы логов Apache для генерации."""

    # Основные типы логов
    NORMAL = "normal"
    ERROR = "error"

    # mod_jk worker логи
    MOD_JK_WORKER_INIT = "mod_jk_worker_init"
    MOD_JK_WORKER_ERROR = "mod_jk_worker_error"

    # jk2 child process логи
    JK2_CHILD_INIT = "jk2_child_init"
    JK2_CHILD_ERROR = "jk2_child_error"

    # Client error логи
    CLIENT_DIRECTORY_FORBIDDEN = "client_directory_forbidden"
    CLIENT_FILE_NOT_FOUND = "client_file_not_found"

    # System notice логи
    SYSTEM_NOTICE = "system_notice"


class IncidentType(Enum):
    """Типы инцидентов для генерации."""

    WORKER_ERROR = "worker_error"
    CONNECTION_FAILED = "connection_failed"
    MEMORY_LEAK = "memory_leak"
    SERVICE_CRASH = "service_crash"
    AUTHENTICATION_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class LogEntry:
    """Представление одной записи лога."""

    timestamp: datetime
    level: LogLevel
    message: str
    process_id: int | None = None
    slot: int | None = None

    def format(self) -> str:
        """Форматирует запись лога в Apache формат.

        Returns:
            Отформатированная строка лога

        """
        # Форматируем timestamp в Apache формате: [Sun Dec 04 04:47:44 2005]
        time_str = self.timestamp.strftime("[%a %b %d %H:%M:%S %Y]")
        level_str = f"[{self.level.value}]"

        return f"{time_str} {level_str} {self.message}"


@dataclass
class GeneratorConfig:
    """Конфигурация генератора логов."""

    # Общие параметры
    start_time: datetime = field(default_factory=datetime.now)
    log_count: int = 100
    time_increment_seconds: tuple[int, int] = (1, 30)

    # Параметры процессов
    process_id_range: tuple[int, int] = (6000, 7000)
    slot_range: tuple[int, int] = (1, 10)

    # Вероятности событий (0.0 - 1.0)
    error_probability: float = 0.15
    incident_probability: float = 0.05

    # Параметры инцидентов
    incident_types: list[IncidentType] = field(
        default_factory=lambda: list(IncidentType)
    )
    incident_duration_logs: tuple[int, int] = (3, 10)

    # Веса для типов логов (определяет частоту каждого типа)
    log_type_weights: dict[str, float] = field(
        default_factory=lambda: {
            "mod_jk_worker_init": 0.25,
            "mod_jk_worker_error": 0.10,
            "jk2_child_init": 0.25,
            "client_directory_forbidden": 0.15,
            "system_notice": 0.15,
            "incidents": 0.10,
        }
    )

    # Параметры client IP адресов
    client_ip_ranges: list[str] = field(
        default_factory=lambda: [
            "192.168.0.0/16",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "public",  # случайные публичные IP
        ]
    )

    # Пути к ресурсам для client errors
    forbidden_paths: list[str] = field(
        default_factory=lambda: [
            "/var/www/html/",
            "/admin/",
            "/config/",
            "/etc/passwd",
            "/var/log/",
        ]
    )


class LogGenerator:
    """Генератор реалистичных Apache/mod_jk логов.

    Класс предоставляет методы для генерации нормальных логов работы сервера
    и различных типов инцидентов с настраиваемыми параметрами.
    """

    # Шаблоны сообщений для нормальных логов
    NORMAL_MESSAGES = [
        "workerEnv.init() ok /etc/httpd/conf/workers2.properties",
        "jk2_init() Found child {pid} in scoreboard slot {slot}",
        "Apache/2.2.3 configured -- resuming normal operations",
        "Server built: {date}",
        "prefork.c: Child process {pid} is entering scoreboard slot {slot}",
    ]

    # Шаблоны mod_jk worker логов (реальные из репозитория)
    MOD_JK_WORKER_MESSAGES = [
        "workerEnv.init() ok /etc/httpd/conf/workers2.properties",
        "workerEnv.init() ok /etc/httpd/conf/workers.properties",
    ]

    # Шаблоны mod_jk worker ошибок
    MOD_JK_WORKER_ERROR_MESSAGES = [
        "mod_jk child workerEnv in error state {state}",
        "mod_jk child init {code} -2",
    ]

    # Шаблоны jk2 child init логов
    JK2_CHILD_INIT_MESSAGES = [
        "jk2_init() Found child {pid} in scoreboard slot {slot}",
        "jk2_init() Found child {pid} in scoreboard slot {slot}",
    ]

    # Шаблоны jk2 ошибок
    JK2_CHILD_ERROR_MESSAGES = [
        "jk2_init() Can't find child {pid} in scoreboard",
    ]

    # Шаблоны client errors
    CLIENT_DIRECTORY_FORBIDDEN_MESSAGES = [
        "[client {client_ip}] Directory index forbidden by rule: {path}",
    ]

    CLIENT_FILE_NOT_FOUND_MESSAGES = [
        "[client {client_ip}] File does not exist: {path}",
        "[client {client_ip}] script not found or unable to stat: {path}",
    ]

    # Шаблоны system notices
    SYSTEM_NOTICE_MESSAGES = [
        "Apache/2.2.3 configured -- resuming normal operations",
        "Server built: {date}",
        "caught SIGTERM, shutting down",
        "SIGHUP received. Attempting to restart",
    ]

    # Шаблоны для ошибок
    ERROR_MESSAGES = [
        "mod_jk child workerEnv in error state {state}",
        "ajp_connection_tcp_get_message: Error receiving message",
        "ajp_send_request: Connection reset by peer or network problems",
        "Child {pid}: Encountered too many errors accepting client connections",
    ]

    # Шаблоны для критических инцидентов
    INCIDENT_MESSAGES = {
        IncidentType.WORKER_ERROR: [
            "mod_jk child workerEnv in critical error state {state}",
            "Worker process {pid} failed to initialize",
            "All workers in error state, service degraded",
        ],
        IncidentType.CONNECTION_FAILED: [
            "Connection to backend server failed after {attempts} attempts",
            "Backend connection pool exhausted",
            "Unable to establish connection to worker node",
        ],
        IncidentType.MEMORY_LEAK: [
            "Memory allocation failed for worker {pid}",
            "Process {pid} exceeding memory limit: {memory}MB",
            "System memory critically low, killing processes",
        ],
        IncidentType.SERVICE_CRASH: [
            "Child process {pid} terminated by signal {signal}",
            "Segmentation fault in worker process {pid}",
            "Fatal error in module mod_jk, shutting down",
        ],
        IncidentType.AUTHENTICATION_FAILURE: [
            "Authentication failed for user '{user}' from {ip}",
            "Multiple failed login attempts detected from {ip}",
            "Possible brute force attack from {ip}",
        ],
        IncidentType.PERMISSION_DENIED: [
            "Permission denied: user '{user}' cannot access {resource}",
            "Access forbidden for {ip}: insufficient privileges",
            "Security violation: unauthorized access attempt to {resource}",
        ],
        IncidentType.RESOURCE_EXHAUSTION: [
            "Server reached MaxClients setting, refusing new connections",
            "File descriptor limit reached, cannot accept connections",
            "Thread pool exhausted, queuing requests",
        ],
    }

    def __init__(self, config: GeneratorConfig | None = None) -> None:
        """Инициализация генератора логов.

        Args:
            config: Конфигурация генератора. Если None, используются
                   значения по умолчанию.

        """
        self.config = config or GeneratorConfig()
        self.logs: list[LogEntry] = []
        self.current_time = self.config.start_time

    def _increment_time(self) -> None:
        """Увеличивает текущее время на случайный интервал."""
        min_sec, max_sec = self.config.time_increment_seconds
        increment = random.randint(min_sec, max_sec)
        self.current_time += timedelta(seconds=increment)

    def _get_random_pid(self) -> int:
        """Возвращает случайный PID из заданного диапазона."""
        return random.randint(*self.config.process_id_range)

    def _get_random_slot(self) -> int:
        """Возвращает случайный номер слота из заданного диапазона."""
        return random.randint(*self.config.slot_range)

    def _generate_random_ip(self) -> str:
        """Генерирует случайный IP адрес."""
        return (
            f"{random.randint(1, 255)}.{random.randint(1, 255)}."
            f"{random.randint(1, 255)}.{random.randint(1, 255)}"
        )

    def _get_random_path(self) -> str:
        """Возвращает случайный путь из списка запрещённых путей."""
        return random.choice(self.config.forbidden_paths)

    def generate_mod_jk_worker_init(self) -> LogEntry:
        """Генерирует лог инициализации mod_jk worker.

        Returns:
            Сгенерированная запись лога

        """
        template = random.choice(self.MOD_JK_WORKER_MESSAGES)

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.NOTICE,
            message=template,
        )

    def generate_mod_jk_worker_error(self) -> LogEntry:
        """Генерирует лог ошибки mod_jk worker.

        Returns:
            Сгенерированная запись об ошибке

        """
        template = random.choice(self.MOD_JK_WORKER_ERROR_MESSAGES)
        message = template.format(
            state=random.randint(6, 10),
            code=random.randint(1, 3),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.ERROR,
            message=message,
        )

    def generate_jk2_child_init(self) -> LogEntry:
        """Генерирует лог инициализации jk2 child процесса.

        Returns:
            Сгенерированная запись лога

        """
        template = random.choice(self.JK2_CHILD_INIT_MESSAGES)
        message = template.format(
            pid=self._get_random_pid(),
            slot=self._get_random_slot(),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.NOTICE,
            message=message,
        )

    def generate_jk2_child_error(self) -> LogEntry:
        """Генерирует лог ошибки jk2 child процесса.

        Returns:
            Сгенерированная запись об ошибке

        """
        template = random.choice(self.JK2_CHILD_ERROR_MESSAGES)
        message = template.format(
            pid=self._get_random_pid(),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.ERROR,
            message=message,
        )

    def generate_client_directory_forbidden(self) -> LogEntry:
        """Генерирует лог запрещённого доступа клиента к директории.

        Returns:
            Сгенерированная запись об ошибке

        """
        template = random.choice(self.CLIENT_DIRECTORY_FORBIDDEN_MESSAGES)
        message = template.format(
            client_ip=self._generate_random_ip(),
            path=self._get_random_path(),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.ERROR,
            message=message,
        )

    def generate_client_file_not_found(self) -> LogEntry:
        """Генерирует лог файла не найденного клиентом.

        Returns:
            Сгенерированная запись об ошибке

        """
        template = random.choice(self.CLIENT_FILE_NOT_FOUND_MESSAGES)
        message = template.format(
            client_ip=self._generate_random_ip(),
            path=self._get_random_path(),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.ERROR,
            message=message,
        )

    def generate_system_notice(self) -> LogEntry:
        """Генерирует системный notice лог.

        Returns:
            Сгенерированная запись лога

        """
        template = random.choice(self.SYSTEM_NOTICE_MESSAGES)
        message = template.format(
            date=self.current_time.strftime("%b %d %Y %H:%M:%S"),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=LogLevel.NOTICE,
            message=message,
        )

    def generate_normal_log(self) -> LogEntry:
        """Генерирует нормальную запись лога (notice или info).

        Returns:
            Сгенерированная запись лога

        """
        level = LogLevel.NOTICE
        template = random.choice(self.NORMAL_MESSAGES)

        # Форматируем сообщение с подстановкой параметров
        message = template.format(
            pid=self._get_random_pid(),
            slot=self._get_random_slot(),
            date=self.current_time.strftime("%b %d %Y %H:%M:%S"),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=level,
            message=message,
        )

    def generate_error_log(self) -> LogEntry:
        """Генерирует запись об ошибке.

        Returns:
            Сгенерированная запись об ошибке

        """
        level = LogLevel.ERROR
        template = random.choice(self.ERROR_MESSAGES)

        message = template.format(
            pid=self._get_random_pid(),
            slot=self._get_random_slot(),
            state=random.randint(1, 10),
        )

        return LogEntry(
            timestamp=self.current_time,
            level=level,
            message=message,
        )

    def generate_incident(
        self,
        incident_type: IncidentType | None = None,
    ) -> list[LogEntry]:
        """Генерирует серию логов, представляющих инцидент.

        Args:
            incident_type: Тип инцидента. Если None, выбирается случайно.

        Returns:
            Список записей логов, составляющих инцидент

        """
        if incident_type is None:
            incident_type = random.choice(self.config.incident_types)

        incident_logs: list[LogEntry] = []
        templates = self.INCIDENT_MESSAGES[incident_type]

        # Определяем количество логов в инциденте
        log_count = random.randint(*self.config.incident_duration_logs)

        for _ in range(log_count):
            self._increment_time()
            template = random.choice(templates)

            # Подготавливаем параметры для разных типов инцидентов
            params = {
                "pid": self._get_random_pid(),
                "slot": self._get_random_slot(),
                "state": random.randint(5, 15),
                "attempts": random.randint(3, 10),
                "memory": random.randint(512, 2048),
                "signal": random.choice([11, 9, 15, 6]),
                "user": random.choice(["admin", "user", "guest", "root"]),
                "ip": f"{random.randint(1, 255)}.{random.randint(1, 255)}"
                f".{random.randint(1, 255)}.{random.randint(1, 255)}",
                "resource": random.choice(
                    ["/admin", "/config", "/etc/passwd", "/var/log"]
                ),
            }

            message = template.format(**params)

            # Критические инциденты помечаем как CRITICAL или ERROR
            level = (
                LogLevel.CRITICAL
                if incident_type
                in [
                    IncidentType.SERVICE_CRASH,
                    IncidentType.RESOURCE_EXHAUSTION,
                ]
                else LogLevel.ERROR
            )

            incident_logs.append(
                LogEntry(
                    timestamp=self.current_time,
                    level=level,
                    message=message,
                )
            )

        return incident_logs

    def generate_logs(self) -> list[LogEntry]:
        """Генерирует набор логов согласно конфигурации.

        Returns:
            Список сгенерированных записей логов

        """
        self.logs = []

        # Подготовка весов для выбора типа лога
        log_types = list(self.config.log_type_weights.keys())
        weights = list(self.config.log_type_weights.values())

        # Словарь с маппингом типов логов на методы генерации
        log_type_generators = {
            LogType.NORMAL: self.generate_normal_log,
            LogType.ERROR: self.generate_error_log,
            LogType.MOD_JK_WORKER_INIT: self.generate_mod_jk_worker_init,
            LogType.MOD_JK_WORKER_ERROR: self.generate_mod_jk_worker_error,
            LogType.JK2_CHILD_INIT: self.generate_jk2_child_init,
            LogType.JK2_CHILD_ERROR: self.generate_jk2_child_error,
            LogType.CLIENT_DIRECTORY_FORBIDDEN: (
                self.generate_client_directory_forbidden
            ),
            LogType.CLIENT_FILE_NOT_FOUND: self.generate_client_file_not_found,
            LogType.SYSTEM_NOTICE: self.generate_system_notice,
        }

        for _ in range(self.config.log_count):
            self._increment_time()

            # Определяем тип лога на основе вероятностей
            rand_val = random.random()

            if rand_val < self.config.incident_probability:
                # Генерируем инцидент
                incident_logs = self.generate_incident()
                self.logs.extend(incident_logs)
            else:
                # Выбираем тип лога на основе весов
                selected_type = random.choices(log_types, weights=weights, k=1)[0]

                # Генерируем соответствующий лог
                generator_method = log_type_generators.get(selected_type)
                if generator_method:
                    self.logs.append(generator_method())
                else:
                    # Fallback на нормальный лог
                    self.logs.append(self.generate_normal_log())

        return self.logs

    def save_to_file(self, filepath: Path | str) -> None:
        """Сохраняет сгенерированные логи в файл.

        Args:
            filepath: Путь к файлу для сохранения логов

        """
        filepath = Path(filepath)

        # Создаём директорию, если её нет
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with filepath.open("w", encoding="utf-8") as file:
            for log in self.logs:
                file.write(log.format() + "\n")

    def get_formatted_logs(self) -> str:
        """Возвращает все логи в виде отформатированной строки.

        Returns:
            Строка со всеми логами

        """
        return "\n".join(log.format() for log in self.logs)


def log_generation() -> None:
    """Пример использования генератора логов."""
    # Создаём конфигурацию
    config = GeneratorConfig(
        log_count=50,
        error_probability=0.2,
        incident_probability=0.1,
        time_increment_seconds=(5, 20),
    )

    # Создаём генератор
    generator = LogGenerator(config)

    # Генерируем логи
    logs = generator.generate_logs()

    # Выводим статистику
    print(f"Сгенерировано логов: {len(logs)}")
    print(f"Период: {logs[0].timestamp} - {logs[-1].timestamp}")
    print("\nПример логов:\n")
    print(generator.get_formatted_logs()[:1000])

    # Сохраняем в файл
    output_file = Path("generated_logs.log")
    generator.save_to_file(output_file)
    print(f"\n✓ Логи сохранены в файл: {output_file.absolute()}")


if __name__ == "__main__":
    log_generation()
