"""Module for collecting logs from neighboring directories (excluding self)."""

import shutil
from pathlib import Path

from settings_analyse import LOG_FILE_PATTERN, PROCESSED_LOG_PATH, SOURCE_LOG_PATH, IGNORED_PATHS


def is_subpath_of(parent: Path, child: Path) -> bool:
    """Check if child path is inside parent path."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def collect_logs():
    """Collects log files from all directories adjacent to 'ai_cyberlogagent'
    and copies them to the processed logs directory.
    Does NOT collect logs from ai_cyberlogagent or its subdirectories.
    Also ignores logs from app_simulation/log_gen/examples.
    """
    # Определяем путь к текущей директории проекта
    current_dir = Path(__file__).parent.parent  # ai_cyberlogagent/default_logs_analyse → ai_cyberlogagent
    parent_dir = current_dir.parent  # Родитель ai_cyberlogagent

    # Paths to ignore
    ignored_paths = [parent_dir / ignore for ignore in IGNORED_PATHS]

    processed_path = Path(PROCESSED_LOG_PATH)
    processed_path.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Searching for log files in sibling directories of: {current_dir.name}")
    print(f"📁 Parent directory: {parent_dir}")

    collected_count = 0

    # Проходим по всем элементам на уровне родителя
    for sibling in parent_dir.iterdir():
        if sibling.is_dir() and sibling != current_dir:
            print(f"\n📂 Checking directory: {sibling.name}")
            # Ищем все лог-файлы по шаблону в соседней папке и подпапках
            log_files = sibling.rglob(LOG_FILE_PATTERN)
            for log_file in log_files:
                try:
                    # Пропускаем, если файл в одном из игнорируемых путей
                    ignored = False
                    for ignore_path in ignored_paths:
                        if is_subpath_of(ignore_path, log_file.resolve()):
                            rel_part = log_file.relative_to(ignore_path) if ignore_path != log_file else log_file.name
                            print(f"  ⚠️  Ignored (in {ignore_path.name}): {rel_part}")
                            ignored = True
                            break
                    if ignored:
                        continue

                    target_file = processed_path / f"{sibling.name}__{log_file.name}"
                    shutil.copy2(log_file, target_file)
                    print(f"  ✅ Collected: {log_file.relative_to(parent_dir)}")
                    collected_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to collect {log_file.name}: {e}")

    # Обработка SOURCE_LOG_PATH, если задан
    if SOURCE_LOG_PATH:
        source_path = Path(SOURCE_LOG_PATH)
        if source_path.exists():
            print(f"\n🔍 Checking custom source path: {source_path}")

            # Проверяем, не находится ли SOURCE_LOG_PATH внутри ai_cyberlogagent
            source_in_ignored = any(is_subpath_of(ignore_path, source_path.resolve()) for ignore_path in ignored_paths)
            if source_in_ignored:
                print(f"  ⚠️  Source path is in ignore list — ignoring: {source_path}")
            else:
                log_files = source_path.rglob(LOG_FILE_PATTERN)
                for log_file in log_files:
                    try:
                        # Проверка на наличие в путях исключения
                        log_resolved = log_file.resolve()
                        ignored = any(is_subpath_of(ignore_path, log_resolved) for ignore_path in ignored_paths)
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

    print(f"\n✅ Total logs collected: {collected_count}")


def main():
    """Main function to run the log collector."""
    print("🚀 Starting log collection from neighboring directories...")
    collect_logs()
    print("🎉 Log collection completed.")


if __name__ == "__main__":
    main()