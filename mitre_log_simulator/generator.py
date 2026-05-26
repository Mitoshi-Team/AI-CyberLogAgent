#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
import random
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PG_APPLICATIONS = ["postgres", "psql", "api", "reporting", "etl"]
PG_DATABASES = ["appdb", "analytics", "audit", "warehouse"]
PG_USERS = ["appuser", "readonly", "replicator", "postgres"]
PG_MESSAGES = [
    "connection authorized: user={user} database={database} application_name={application}",
    "statement: SELECT id, username FROM sessions WHERE active = true LIMIT 10;",
    "statement: UPDATE accounts SET locked = true WHERE last_login < now() - interval '365 days';",
    "duration: {duration} ms execute <unnamed>: INSERT INTO audit_log(event, source) VALUES ('login', 'web');",
    "autovacuum: processing database '{database}'",
    "checkpoint starting: time",
    "temporary file: path \"base/pgsql_tmp/pgsql_tmp{pid}.0\" size {size} bytes",
]


@dataclass(frozen=True)
class SimulatorConfig:
    technique: str | None
    random_attacks: bool
    no_attacks: bool
    interval_seconds: int
    noise_batch_size: int
    output_dir: Path
    log_file: Path
    timeline_file: Path
    markers_file: Path
    host_output_dir: Path | None
    host_log_file: Path | None
    host_timeline_file: Path | None
    host_markers_file: Path | None
    preferred_platforms: list[str] | None
    atomics_folder: Path


class OutputSink:
    def __init__(self, stream, file_handles: list[object]):
        self._stream = stream
        self._file_handles = file_handles

    def write_line(self, message: str) -> None:
        self._stream.write(message + "\n")
        self._stream.flush()
        for fh in self._file_handles:
            try:
                fh.write(message + "\n")
                fh.flush()
            except Exception:
                # best-effort: ignore host write failures
                pass


class SignalState:
    def __init__(self) -> None:
        self.stop_requested = False


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_bool(raw: str | None) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def random_default_int(raw_env: str | None, minimum: int, maximum: int) -> int:
    if raw_env is not None and raw_env.strip():
        return int(raw_env)
    return random.randint(minimum, maximum)


def parse_config() -> SimulatorConfig:
    parser = argparse.ArgumentParser(description="Generate mixed background logs and Atomic Red Team attacks.")
    parser.add_argument("--technique", default=os.getenv("SIM_TECHNIQUE") or None)
    parser.add_argument("--random-attacks", action="store_true", default=parse_bool(os.getenv("SIM_RANDOM_ATTACKS")))
    parser.add_argument("--no-attacks", action="store_true", default=parse_bool(os.getenv("SIM_NO_ATTACKS")))
    parser.add_argument("--interval-seconds", type=int, default=random_default_int(os.getenv("SIM_INTERVAL_SECONDS"), 10, 30))
    parser.add_argument("--noise-batch-size", type=int, default=random_default_int(os.getenv("SIM_NOISE_BATCH_SIZE"), 50, 100))
    parser.add_argument("--output-dir", default=os.getenv("SIM_OUTPUT_DIR", "/app/output"))
    parser.add_argument("--log-file", default=os.getenv("SIM_LOG_FILE", "/app/output/generated_logs.log"))
    parser.add_argument("--timeline-file", default=os.getenv("SIM_TIMELINE_FILE", "/app/output/attack_timeline.log"))
    parser.add_argument("--markers-file", default=os.getenv("SIM_MARKERS_FILE", "/app/output/attack_markers.csv"))
    parser.add_argument("--host-output-dir", default=os.getenv("SIM_HOST_OUTPUT_DIR") or None)
    parser.add_argument("--preferred-platforms", default=os.getenv("SIM_PREFERRED_PLATFORMS") or None)
    parser.add_argument("--atomics-folder", default=os.getenv("SIM_ATOMICS_FOLDER", "/opt/atomic-red-team/atomics"))

    args = parser.parse_args()

    return SimulatorConfig(
        technique=args.technique,
        random_attacks=args.random_attacks,
        no_attacks=args.no_attacks,
        interval_seconds=max(1, args.interval_seconds),
        noise_batch_size=max(1, args.noise_batch_size),
        output_dir=Path(args.output_dir),
        log_file=Path(args.log_file),
        timeline_file=Path(args.timeline_file),
        markers_file=Path(args.markers_file),
        host_output_dir=Path(args.host_output_dir) if args.host_output_dir else None,
        host_log_file=(Path(args.host_output_dir) / Path(args.log_file).name) if args.host_output_dir else None,
        host_timeline_file=(Path(args.host_output_dir) / Path(args.timeline_file).name) if args.host_output_dir else None,
        host_markers_file=(Path(args.host_output_dir) / Path(args.markers_file).name) if args.host_output_dir else None,
        preferred_platforms=[p.strip().lower() for p in args.preferred_platforms.split(',')] if args.preferred_platforms else None,
        atomics_folder=Path(args.atomics_folder),
    )


def setup_signal_handlers(state: SignalState) -> None:
    def handle_signal(_signum, _frame):
        state.stop_requested = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)


def ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def emit_flog_batch(sink: OutputSink, log_format: str, count: int) -> None:
    command = ["flog", "-t", "stdout", "-f", log_format, "-n", str(count)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    assert process.stdout is not None
    for line in process.stdout:
        sink.write_line(line.rstrip("\n"))
    exit_code = process.wait()
    if exit_code != 0:
        sink.write_line(f"{utc_timestamp()} [noise][flog] format={log_format} exit_code={exit_code}")


def emit_postgres_batch(sink: OutputSink, count: int) -> None:
    for _ in range(count):
        pid = random.randint(2000, 65000)
        duration = round(random.uniform(0.5, 250.0), 2)
        size = random.randint(128, 16384)
        message = random.choice(PG_MESSAGES).format(
            user=random.choice(PG_USERS),
            database=random.choice(PG_DATABASES),
            application=random.choice(PG_APPLICATIONS),
            duration=duration,
            pid=pid,
            size=size,
        )
        sink.write_line(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC [{pid}] LOG:  {message}"
        )


def emit_background_noise(sink: OutputSink, batch_size: int) -> None:
    web_count = max(1, batch_size)
    emit_flog_batch(sink, "apache_combined", web_count)


def discover_candidate_techniques(atomics_folder: Path, preferred_platforms: list[str] | None = None) -> list[str]:
    candidates: list[str] = []
    if not atomics_folder.exists():
        return candidates

    exclusion_tokens = ("windows", "powershell", "powercli", "esxi", "hyper-v", "winrm")
    inclusion_tokens = ("linux", "macos", "container", "containers")

    for technique_dir in sorted(atomics_folder.glob("T*")):
        if not technique_dir.is_dir():
            continue
        yaml_path = technique_dir / f"{technique_dir.name}.yaml"
        if not yaml_path.exists():
            continue
        yaml_text = yaml_path.read_text(encoding="utf-8", errors="ignore").lower()

        # Skip techniques that clearly target Windows/PowerShell/ESXi unless user explicitly requested them
        if any(tok in yaml_text for tok in exclusion_tokens):
            # if preferred_platforms explicitly includes windows, allow it
            if not preferred_platforms or not any(p in ("windows", "win") for p in preferred_platforms):
                continue

        if preferred_platforms:
            # require at least one preferred platform token to be present
            if any(p in yaml_text for p in preferred_platforms):
                candidates.append(technique_dir.name)
        else:
            # prefer techniques with linux/macos/container targets
            if any(tok in yaml_text for tok in inclusion_tokens):
                candidates.append(technique_dir.name)

    return candidates


def run_atomic_test(sink: OutputSink, config: SimulatorConfig, technique: str) -> None:
    start = datetime.now(timezone.utc)

    command = [
        "pwsh",
        "-NoLogo",
        "-Command",
        (
            "Import-Module Invoke-AtomicRedTeam -Force; "
            f"Invoke-AtomicTest {ps_quote(technique)} "
            f"-PathToAtomicsFolder {ps_quote(str(config.atomics_folder))} "
            "-NoExecutionLog -Force -SupressPathToAtomicsFolder"
        ),
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    exit_code = process.wait()

    end = datetime.now(timezone.utc)
    line = "|".join([
        start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        technique,
    ]) + "\n"
    # write timeline to primary location
    with config.timeline_file.open("a", encoding="utf-8") as timeline_handle:
        timeline_handle.write(line)

    # also write to host timeline if configured
    if config.host_timeline_file:
        try:
            with config.host_timeline_file.open("a", encoding="utf-8") as host_tl:
                host_tl.write(line)
        except Exception:
            pass

    row = [start.isoformat(timespec="seconds").replace("+00:00", "Z"), end.isoformat(timespec="seconds").replace("+00:00", "Z"), technique]
    with config.markers_file.open("a", encoding="utf-8", newline="") as markers_handle:
        writer = csv.writer(markers_handle)
        writer.writerow(row)

    if config.host_markers_file:
        try:
            with config.host_markers_file.open("a", encoding="utf-8", newline="") as host_markers:
                writer = csv.writer(host_markers)
                writer.writerow(row)
        except Exception:
            pass


def choose_technique(config: SimulatorConfig, candidates: list[str]) -> str | None:
    if config.no_attacks:
        return None
    if config.random_attacks:
        if not candidates:
            return None
        return random.choice(candidates)
    return config.technique


def validate_mode(config: SimulatorConfig) -> None:
    selected_modes = sum([bool(config.technique), config.random_attacks, config.no_attacks])
    if selected_modes > 1:
        raise SystemExit("Only one attack mode can be enabled at a time: --technique, --random-attacks, or --no-attacks.")


def main() -> int:
    config = parse_config()
    validate_mode(config)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    config.timeline_file.parent.mkdir(parents=True, exist_ok=True)
    config.markers_file.parent.mkdir(parents=True, exist_ok=True)

    if config.host_output_dir:
        config.host_output_dir.mkdir(parents=True, exist_ok=True)

    if not config.timeline_file.exists():
        config.timeline_file.touch()

    if not config.markers_file.exists():
        with config.markers_file.open("w", encoding="utf-8", newline="") as markers_handle:
            writer = csv.writer(markers_handle)
            writer.writerow(["timestamp_start", "timestamp_end", "technique"])

    file_handles = []
    log_handle = config.log_file.open("a", encoding="utf-8", buffering=1)
    file_handles.append(log_handle)
    host_log_handle = None
    if config.host_log_file:
        try:
            host_log_handle = config.host_log_file.open("a", encoding="utf-8", buffering=1)
            file_handles.append(host_log_handle)
        except Exception:
            host_log_handle = None

    sink = OutputSink(sys.stdout, file_handles)
    state = SignalState()
    setup_signal_handlers(state)

    try:
        candidates = discover_candidate_techniques(config.atomics_folder, config.preferred_platforms)

        while not state.stop_requested:
            emit_background_noise(sink, config.noise_batch_size)

            technique = choose_technique(config, candidates)
            if technique:
                run_atomic_test(sink, config, technique)

            if state.stop_requested:
                break

            deadline = time.monotonic() + config.interval_seconds
            while time.monotonic() < deadline and not state.stop_requested:
                time.sleep(min(1.0, deadline - time.monotonic()))

    finally:
        for fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())