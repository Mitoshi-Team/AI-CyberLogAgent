"""
Init file for the default_logs_analyse package.
"""

# Import main functions for easy access
from .log_collector import collect_logs, main as collect_main
from .log_analyzer import analyze_logs, main as analyze_main

__all__ = [
    'collect_logs',
    'analyze_logs',
    'collect_main',
    'analyze_main'
]