"""Модуль генерации логов AI-CyberLogAgent.

Предоставляет инструменты для генерации реалистичных логов веб-сервера
Apache/mod_jk с возможностью симуляции различных инцидентов безопасности.
"""

from .config_loader import ConfigLoader
from .log_gen import (
    GeneratorConfig,
    IncidentType,
    LogEntry,
    LogGenerator,
    LogLevel,
    LogType,
)

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
