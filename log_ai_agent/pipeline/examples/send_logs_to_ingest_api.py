"""Send local log files to AI-CyberLogAgent ingest API.

Usage:
    python send_logs_to_ingest_api.py --api http://localhost:8000 --source ext-agent --dir ./sample-logs
"""

from __future__ import annotations

import argparse
from pathlib import Path
from tkinter import Tk, filedialog

import requests


def iter_log_files(directory: Path) -> list[Path]:
    """Collect .log and .txt files recursively."""
    files = list(directory.rglob("*.log"))
    files.extend(directory.rglob("*.txt"))
    return sorted(set(files))


def pick_files_via_explorer() -> list[Path]:
    """Open OS file picker and return selected log files."""
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    selected = filedialog.askopenfilenames(
        title="Выберите лог-файлы",
        filetypes=[
            ("Log files", "*.log *.txt"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()

    files = [Path(path) for path in selected]
    return [file for file in files if file.suffix.lower() in {".log", ".txt"}]


def pick_dir_via_explorer() -> Path | None:
    """Open OS folder picker and return selected directory."""
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    selected = filedialog.askdirecяtory(title="Выберите папку с логами")
    root.destroy()

    if not selected:
        return None
    return Path(selected)


def upload_file(api_base: str, file_path: Path, source: str, timeout: int = 30) -> dict:
    """Upload one log file to /api/pipeline/logs/upload."""
    url = f"{api_base.rstrip('/')}/api/pipeline/logs/upload"

    with file_path.open("rb") as fp:
        response = requests.post(
            url,
            data={"source": source},
            files={"file": (file_path.name, fp, "text/plain")},
            timeout=timeout,
        )

    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload log files to ingest API")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--source", default="external-client", help="Source label for uploaded logs")
    parser.add_argument("--dir", help="Directory with .log/.txt files")
    parser.add_argument(
        "--pick-files",
        action="store_true",
        help="Open file picker and choose one or more .log/.txt files",
    )
    parser.add_argument(
        "--pick-dir",
        action="store_true",
        help="Open folder picker and choose a directory with logs",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    args = parser.parse_args()

    files: list[Path] = []

    if args.pick_files:
        files = pick_files_via_explorer()
    elif args.pick_dir:
        logs_dir = pick_dir_via_explorer()
        if logs_dir is None:
            print("No folder selected")
            return
        files = iter_log_files(logs_dir)
    elif args.dir:
        logs_dir = Path(args.dir)
        if not logs_dir.exists() or not logs_dir.is_dir():
            raise SystemExit(f"Directory not found: {logs_dir}")
        files = iter_log_files(logs_dir)
    else:
        print("No --dir provided. Opening file picker...")
        files = pick_files_via_explorer()

        if not files:
            print("No files selected. Opening folder picker...")
            logs_dir = pick_dir_via_explorer()
            if logs_dir is not None:
                files = iter_log_files(logs_dir)

    if not files:
        print("No .log or .txt files found")
        return

    print(f"Found {len(files)} files. Uploading to {args.api} ...")

    success = 0
    failed = 0

    for file_path in files:
        try:
            result = upload_file(args.api, file_path, args.source, args.timeout)
            success += 1
            print(f"[OK] {file_path} -> {result.get('path')}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {file_path}: {exc}")

    print(f"Done. success={success}, failed={failed}")


if __name__ == "__main__":
    main()
