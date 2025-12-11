"""Module for collecting analyse_logs from neighboring directories (excluding self)."""

import shutil
from pathlib import Path

from .settings import (
    IGNORED_PATHS,
    LOG_FILE_PATTERN,
    PROCESSED_LOG_PATH,
    SOURCE_LOG_PATH,
)


def is_subpath_of(parent: Path, child: Path) -> bool:
    """Check if child path is inside parent path."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def collect_logs():
    """Collects log files from all directories adjacent to 'log_ai_agent'
    and copies them to the processed analyse_logs directory.
    Does NOT collect analyse_logs from log_ai_agent or its subdirectories.
    Also ignores analyse_logs from app_simulation/log_gen/examples.
    """
    # Определяем путь к текущей директории проекта
    current_dir = Path(
        __file__
    ).parent.parent  # log_ai_agent/default_logs_analyse → log_ai_agent
    parent_dir = current_dir.parent  # Родитель log_ai_agent

    # Paths to ignore
    ignored_paths = [parent_dir / ignore for ignore in IGNORED_PATHS]

    processed_path = Path(PROCESSED_LOG_PATH)
    processed_path.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Searching for log files in sibling directories of: {current_dir.name}")
    print(f"📁 Parent directory: {parent_dir}")

    collected_count = 0

    # Проходим по всем элементам на уровне родителя, включая файлы в корне
    for item in parent_dir.iterdir():
        if item.is_dir() and item != current_dir:
            print(f"\n📂 Checking directory: {item.name}")
            # Собираем логи из поддиректорий
            log_files = item.rglob(LOG_FILE_PATTERN)
            for log_file in log_files:
                try:
                    # Пропускаем, если файл в одном из игнорируемых путей
                    ignored = False
                    for ignore_path in ignored_paths:
                        if is_subpath_of(ignore_path, log_file.resolve()):
                            rel_part = (
                                log_file.relative_to(ignore_path)
                                if ignore_path != log_file
                                else log_file.name
                            )
                            print(f"  ⚠️  Ignored (in {ignore_path.name}): {rel_part}")
                            ignored = True
                            break
                    if ignored:
                        continue

                    target_file = processed_path / f"{item.name}__{log_file.name}"
                    shutil.copy2(log_file, target_file)
                    print(f"  ✅ Collected: {log_file.relative_to(parent_dir)}")
                    collected_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to collect {log_file.name}: {e}")

    # Ищем лог-файлы непосредственно в корне проекта
    print("\n<📂> Checking root: ")
    root_log_files = parent_dir.glob(LOG_FILE_PATTERN)
    for log_file in root_log_files:
        if log_file.is_file():
            try:
                # Проверяем, не находится ли файл в игнорируемых путях
                log_resolved = log_file.resolve()
                ignored = any(
                    is_subpath_of(ignore_path, log_resolved)
                    for ignore_path in ignored_paths
                )
                if ignored:
                    rel_part = (
                        log_file.relative_to(ignore_path)
                        if ignore_path != log_file
                        else log_file.name
                    )
                    print(f"  ⚠️  Ignored (in {ignore_path.name}): {rel_part}")
                    continue

                target_file = processed_path / f"root__{log_file.name}"
                shutil.copy2(log_file, target_file)
                print(f"  ✅ Collected: {log_file.name}")
                collected_count += 1
            except Exception as e:
                print(f"  ❌ Failed to collect {log_file.name}: {e}")

    # Обработка SOURCE_LOG_PATH, если задан
    if SOURCE_LOG_PATH:
        source_path = Path(SOURCE_LOG_PATH)
        if source_path.exists():
            print(f"\n🔍 Checking custom source path: {source_path}")

            # Проверяем, не находится ли SOURCE_LOG_PATH внутри log_ai_agent
            source_in_ignored = any(
                is_subpath_of(ignore_path, source_path.resolve())
                for ignore_path in ignored_paths
            )
            if source_in_ignored:
                print(f"  ⚠️  Source path is in ignore list — ignoring: {source_path}")
            else:
                log_files = source_path.rglob(LOG_FILE_PATTERN)
                for log_file in log_files:
                    try:
                        # Проверка на наличие в путях исключения
                        log_resolved = log_file.resolve()
                        ignored = any(
                            is_subpath_of(ignore_path, log_resolved)
                            for ignore_path in ignored_paths
                        )
                        if ignored:
                            print(f"  ⚠️  Ignored (in ignore list): {log_file.name}")
                            continue

                        target_file = processed_path / f"source__{log_file.name}"
                        shutil.copy2(log_file, target_file)
                        print(f"  ✅ Collected: {log_file.name}")
                        collected_count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to collect {log_file.name}: {e}")
        else:
            print(f"  ⚠️  SOURCE_LOG_PATH does not exist: {source_path}")

    print(f"\n✅ Total analyse_logs collected: {collected_count}")


def main():
    """Main function to run the log collector."""
    print("🚀 Starting log collection from neighboring directories...")
    collect_logs()
    print("🎉 Log collection completed.")


if __name__ == "__main__":
    main()
