"""Init file for the default_logs_analyse package."""

# Import main functions for easy access
from .log_analyzer import analyze_logs
from .log_analyzer import main as analyze_main
from .log_collector import collect_logs
from .log_collector import main as collect_main

__all__ = ["collect_logs", "analyze_logs", "collect_main", "analyze_main"]
