"""Wrapper для запуска log_gen_cli из директории log_gen.

Этот скрипт позволяет запускать генератор логов прямо из директории log_gen:
    python run_cli.py start imitate attack
    python run_cli.py start record_logs_for_tests stable 1000
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Импортируем и запускаем main из log_gen_cli
from app_simulation.log_gen.log_gen_cli import main

if __name__ == "__main__":
    main()
