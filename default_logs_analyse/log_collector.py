"""
Module for collecting logs from another application.
"""
import os
import shutil
from pathlib import Path

from settings_analyse import SOURCE_LOG_PATH, PROCESSED_LOG_PATH, LOG_FILE_PATTERN


def collect_logs():
    """
    Collects log files from the source directory and copies them
    to the processed logs directory.
    """
    source_path = Path(SOURCE_LOG_PATH)
    processed_path = Path(PROCESSED_LOG_PATH)

    if not source_path.exists():
        print(f"Source log path does not exist: {source_path}")
        return

    processed_path.mkdir(parents=True, exist_ok=True)

    log_files = source_path.glob(LOG_FILE_PATTERN)
    collected_count = 0

    for log_file in log_files:
        try:
            shutil.copy2(log_file, processed_path / log_file.name)
            print(f"Collected: {log_file.name}")
            collected_count += 1
        except Exception as e:
            print(f"Failed to collect {log_file.name}: {e}")

    print(f"\nTotal logs collected: {collected_count}")


def main():
    """Main function to run the log collector."""
    print("Starting log collection...")
    collect_logs()
    print("Log collection completed.")


if __name__ == "__main__":
    main()