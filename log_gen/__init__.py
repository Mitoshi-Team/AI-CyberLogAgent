"""Модуль генерации логов AI-CyberLogAgent.

Предоставляет инструменты для генерации реалистичных логов веб-сервера
Apache/mod_jk с возможностью симуляции различных инцидентов безопасности.
"""


# Используем ленивый импорт для избежания циклических зависимостей
def __getattr__(name):
    if name == "ConfigLoader":
        from .config_loader import ConfigLoader

        return ConfigLoader
    elif name == "GeneratorConfig":
        from .log_gen import GeneratorConfig

        return GeneratorConfig
    elif name == "IncidentType":
        from .log_gen import IncidentType

        return IncidentType
    elif name == "LogEntry":
        from .log_gen import LogEntry

        return LogEntry
    elif name == "LogGenerator":
        from .log_gen import LogGenerator

        return LogGenerator
    elif name == "LogLevel":
        from .log_gen import LogLevel

        return LogLevel
    elif name == "LogType":
        from .log_gen import LogType

        return LogType
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LogGenerator",
    "LogEntry",
    "LogLevel",
    "LogType",
    "IncidentType",
    "GeneratorConfig",
    "ConfigLoader",
]

__version__ = "1.0.0"
__author__ = "AI-CyberLogAgent Team"
