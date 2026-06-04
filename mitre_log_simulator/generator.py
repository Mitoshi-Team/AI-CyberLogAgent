#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
import random
import re
import signal
import subprocess
import sys
import time
import typing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


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
    unknown_file: Path
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
    parser.add_argument("--unknown-file", default=os.getenv("SIM_UNKNOWN_FILE", "/host_output/unknown_techniques.txt"))
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
        unknown_file=Path(args.unknown_file),
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

    for technique_dir in sorted(atomics_folder.glob("T*")):
        if not technique_dir.is_dir():
            continue
        yaml_path = technique_dir / f"{technique_dir.name}.yaml"
        if not yaml_path.exists():
            continue

        if preferred_platforms:
            yaml_text = yaml_path.read_text(encoding="utf-8", errors="ignore").lower()
            if any(p in yaml_text for p in preferred_platforms):
                candidates.append(technique_dir.name)
        else:
            candidates.append(technique_dir.name)

    return candidates


def apache_ts(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%a %b %d %H:%M:%S %Y")


def _src_ip() -> str:
    return f"10.0.{random.randint(0, 255)}.{random.randint(2, 254)}"


def _rand_pid() -> int:
    return random.randint(1000, 9999)


def first_word(command: str) -> str:
    if not command.strip():
        return ""
    parts = command.strip().split()
    if not parts:
        return ""
    first = parts[0].strip("\"'")
    if first.lower() in ("sudo", "time", "nohup", "env", "timeout") and len(parts) > 1:
        first = parts[1].strip("\"'")
    first = first.replace("\\", "/").rsplit("/", 1)[-1]
    if first.lower().endswith(".exe"):
        first = first[:-4]
    return first.lower()


CommandHandler = typing.Callable[[str, str, str], list[str]]


# --- Command handlers ---

def _gen_nmap(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    dst = f"10.0.{random.randint(0, 255)}.{random.randint(2, 254)}"
    return [
        f"[{apache_ts()}] [warning] [client {src}] Possible SYN flood detected from {src}",
        f"[{apache_ts()}] [error] [client {src}] Connection attempt to {dst}:{random.choice([22, 80, 443, 3389, 8080])} rejected",
    ]

def _gen_nc(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'nc\s+(-[a-z]+\s+)?(\S+)\s+(\d+)', command)
    if m:
        return [f"[{apache_ts()}] [warning] [client {src}] Outbound raw connection to {m.group(2)}:{m.group(3)}"]
    return [f"[{apache_ts()}] [warning] [client {src}] Outbound raw connection to external host"]

def _gen_telnet(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'telnet\s+(\S+)', command)
    h = m.group(1) if m else "external-host"
    return [
        f"[{apache_ts()}] [warning] telnet[{_rand_pid()}]: connect from {src} to {h}:23",
        f"[{apache_ts()}] [info] telnetd[{_rand_pid()}]: login from {src}",
    ]

def _gen_net_util(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] {cmd_word} execution: network diagnostic tool",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_packet_cap(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    iface = random.choice(['eth0', 'ens33', 'enp0s3', 'wlan0', 'lo'])
    return [
        f"[{apache_ts()}] [warning] [client {src}] Network packet capture started on {iface}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}",
    ]

def _gen_http(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'https?://([^\s\'">]+)', command)
    target = m.group(1) if m else f"{src}/payload"
    fn = target.rsplit("/", 1)[-1] if "/" in target else "index.html"
    return [
        f"[{apache_ts()}] [error] [client {src}] File does not exist: /{fn}, referer: http://{target}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 5000)} \"-\" \"{cmd_word}/7.81.0\"",
    ]

def _gen_ssh(command: str, cmd_word: str, technique: str) -> list[str]:
    pid = _rand_pid()
    user_m = re.search(r'ssh\s+(\w+)@', command)
    host_m = re.search(r'ssh\s+(?:\w+@)?(\S+)', command)
    u = user_m.group(1) if user_m else "root"
    h = host_m.group(1) if host_m else _src_ip()
    return [
        f"[{apache_ts()}] [info] sshd[{pid}]: Accepted publickey for {u} from {h} port {random.randint(10000, 65000)}",
        f"[{apache_ts()}] [info] sshd[{pid}]: pam_unix(sshd:session): session opened for user {u} (uid={random.randint(1000, 9999)})",
    ]

def _gen_scp(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] sshd[{_rand_pid()}]: Received disconnect from {src}: 11: disconnected by user",
        f"[{apache_ts()}] [info] sftp-server[{_rand_pid()}]: session opened for local user",
    ]

def _gen_script(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [error] [client {src}] POST /cgi-bin/exec.cgi HTTP/1.1\" 500 {random.randint(50, 200)}",
        f"[{apache_ts()}] [error] [client {src}] Script execution failed with exit code {random.choice([1, 2, 126, 127, 255])}",
    ]

def _gen_pkg(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'(?:install|remove)\s+(\S+)', command)
    pkg = m.group(1) if m else "package"
    if cmd_word in ("pip", "pip3", "npm", "gem", "cargo", "choco", "brew"):
        return [
            f"[{apache_ts()}] [info] {cmd_word}[{_rand_pid()}]: installed {pkg}",
            f"[{apache_ts()}] [notice] [client {src}] POST / HTTP/1.1\" 200 {random.randint(100, 500)}",
        ]
    return [
        f"[{apache_ts()}] [info] dpkg[{_rand_pid()}]: {pkg}:amd64 installed",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_powershell(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    snippet = command[:80].replace("\n", " ")
    return [
        f"[{apache_ts()}] [warning] [client {src}] PowerShell execution detected: {snippet}",
        f"[{apache_ts()}] [info] [client {src}] Process created: powershell.exe (PID {_rand_pid()})",
    ]

def _gen_cmd(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] cmd.exe execution: {command[:80].replace(chr(10), ' ')}",
        f"[{apache_ts()}] [info] [client {src}] Process created: cmd.exe (PID {_rand_pid()})",
    ]

def _gen_registry(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'(?:add|delete|modify|set)\s+(\S+)', command)
    key = m.group(1) if m else "HKLM\\SYSTEM\\CurrentControlSet"
    return [
        f"[{apache_ts()}] [warning] [client {src}] Registry modification: {key}",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=setxattr path=/proc/registry",
    ]

def _gen_schtasks(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'(?:/tn|/create)\s+(\S+)', command)
    name = m.group(1) if m else "UpdaterTask"
    return [
        f"[{apache_ts()}] [warning] [client {src}] Scheduled task created: {name}",
        f"[{apache_ts()}] [info] Security: Task Scheduler service registered task \"{name}\"",
    ]

def _gen_wmic(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] WMI query executed",
        f"[{apache_ts()}] [info] WinMgmt[{_rand_pid()}]: WMI operation: {command[:60]}",
    ]

def _gen_certutil(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Certificate operation: {cmd_word}",
        f"[{apache_ts()}] [warning] [client {src}] Suspicious base64 decode via certutil",
    ]

def _gen_bitsadmin(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] BITS job created for file transfer",
        f"[{apache_ts()}] [info] Microsoft-Windows-Bits-Client: Job transferred",
    ]

def _gen_rundll32(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [error] [client {src}] Suspicious DLL execution via rundll32",
        f"[{apache_ts()}] [warning] [client {src}] Process created: rundll32.exe (PID {_rand_pid()})",
    ]

def _gen_mshta(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [error] [client {src}] HTA payload execution detected",
        f"[{apache_ts()}] [warning] [client {src}] mshta.exe executed with script content",
    ]

def _gen_msiexec(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] MSI package installation started",
        f"[{apache_ts()}] [info] MsiInstaller: Product installed successfully",
    ]

def _gen_net_windows(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] Network configuration: {command[:80].replace(chr(10), ' ')}",
        f"[{apache_ts()}] [info] [client {src}] Security: network account modification",
    ]

def _gen_win_script(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] Windows Script Host execution: {cmd_word}",
        f"[{apache_ts()}] [info] [client {src}] Process created: {cmd_word}.exe (PID {_rand_pid()})",
    ]

def _gen_service_windows(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Service control: {command[:80].replace(chr(10), ' ')}",
        f"[{apache_ts()}] [info] Service {random.choice(['created', 'stopped', 'started', 'modified'])} successfully",
    ]

def _gen_vssadmin(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] Volume Shadow Copy operation: {command[:60]}",
        f"[{apache_ts()}] [info] VSS: Shadow copy {'created' if 'create' in command else 'deleted'}",
    ]

def _gen_wevtutil(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] Windows event log cleared or modified",
        f"[{apache_ts()}] [info] Security: Event log was cleared by user",
    ]

def _gen_bcdedit(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] [client {src}] Boot configuration modified",
        f"[{apache_ts()}] [info] [client {src}] BCDEDIT: Windows Boot Manager configuration changed",
    ]

def _gen_file_read(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(rf'{cmd_word}\s+(\S+)', command)
    path = m.group(1) if m else "/etc/passwd"
    return [
        f"[{apache_ts()}] [notice] [client {src}] File content viewed: {path}",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=read path={path}",
    ]

def _gen_echo(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'>\s*(\S+)', command)
    f = m.group(1) if m else "/tmp/file"
    return [
        f"[{apache_ts()}] [error] [client {src}] File created: {f}",
        f"[{apache_ts()}] [info] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(500, 5000)}",
    ]

def _gen_touch(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'touch\s+(\S+)', command)
    f = m.group(1) if m else "/tmp/file"
    return [
        f"[{apache_ts()}] [notice] [client {src}] File timestamp modified: {f}",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=utimensat path={f}",
    ]

def _gen_cp(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] File copied",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=sendfile",
    ]

def _gen_mv(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] File moved",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=rename",
    ]

def _gen_rm(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [error] [client {src}] Mass file deletion detected",
        f"[{apache_ts()}] [warning] auditd[{_rand_pid()}]: syscall=unlinkat count={random.randint(10, 999)}",
    ]

def _gen_archive(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Archive operation: {cmd_word}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_base64(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] Base64 encode/decode operation performed",
        f"[{apache_ts()}] [error] [client {src}] POST /upload.cgi HTTP/1.1\" 200 {random.randint(200, 500)}",
    ]

def _gen_dd(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    dev = random.choice(['sda', 'sdb', 'nvme0n1', 'md0', 'loop0'])
    return [
        f"[{apache_ts()}] [warning] kernel: I/O error on device {dev}, logical block {random.randint(0, 9999)}",
        f"[{apache_ts()}] [notice] [client {src}] Disk write operation: {dev}",
    ]

def _gen_find(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] Filesystem enumeration via find",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=getdents64 cwd=/",
    ]

def _gen_text_tool(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] File content {cmd_word} performed",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=openat flags=O_RDONLY",
    ]

def _gen_whoami(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] User identity queried via {cmd_word}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_sys_info(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [f"[{apache_ts()}] [info] [client {src}] System information queried via {cmd_word}"]

def _gen_net_config(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Network configuration queried via {cmd_word}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_env(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Environment variables accessed",
        f"[{apache_ts()}] [notice] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}",
    ]

def _gen_history(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [f"[{apache_ts()}] [info] [client {src}] Command history accessed"]

def _gen_clear(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [f"[{apache_ts()}] [info] [client {src}] Terminal session cleared"]

def _gen_alias_mod(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [f"[{apache_ts()}] [info] [client {src}] Shell alias modified"]

def _gen_ps(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] Process listing requested via {cmd_word}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}",
    ]

def _gen_kill(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'kill\s+-?\d*\s+(\d+)', command)
    pid = m.group(1) if m else str(_rand_pid())
    sig = random.choice(['TERM', 'KILL', 'HUP', 'INT'])
    return [
        f"[{apache_ts()}] [warning] kernel: process {pid} received SIG{sig}",
        f"[{apache_ts()}] [info] systemd[1]: Unit process-{pid}.scope: Deactivated successfully",
    ]

def _gen_service(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    svc = random.choice(['nginx.service', 'apache2.service', 'sshd.service', 'mysql.service', 'docker.service'])
    return [
        f"[{apache_ts()}] [info] systemd[{_rand_pid()}]: {random.choice(['Stopped', 'Started'])} {svc}",
        f"[{apache_ts()}] [info] [client {src}] Service state changed: {svc}",
    ]

def _gen_cron(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] crontab[{_rand_pid()}]: REPLACE (user)",
        f"[{apache_ts()}] [info] cron[{_rand_pid()}]: (user) CMD (/bin/sh -c \"...\")",
    ]

def _gen_kmod(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = random.choice(['sctp', 'raw', 'af_key', 'tun', 'vxlan', 'overlay'])
    return [
        f"[{apache_ts()}] [warning] kernel: {m}: module loaded by user",
        f"[{apache_ts()}] [info] [client {src}] Kernel module {cmd_word} executed",
    ]

def _gen_mount(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    dev = random.choice(['sda1', 'sdb1', 'nvme0n1p1', 'xvd1', 'loop0'])
    return [
        f"[{apache_ts()}] [notice] kernel: EXT4-fs ({dev}): mounted filesystem",
        f"[{apache_ts()}] [info] [client {src}] Filesystem mounted",
    ]

def _gen_disk(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    dev = random.choice(['sda', 'sdb', 'nvme0n1', 'md0'])
    return [
        f"[{apache_ts()}] [warning] kernel: I/O error on device {dev}, logical block {random.randint(0, 9999)}",
        f"[{apache_ts()}] [notice] [client {src}] Disk {cmd_word} executed",
    ]

def _gen_git(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'git\s+clone\s+(\S+)', command)
    r = m.group(1).rsplit('/', 1)[-1].replace('.git', '') if m else "repository"
    return [
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)} \"-\" \"git/2.34.1\"",
        f"[{apache_ts()}] [info] [client {src}] Repository cloned: {r}",
    ]

def _gen_docker(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [notice] [client {src}] Docker API: POST /containers/create HTTP/1.1",
        f"[{apache_ts()}] [error] [client {src}] Docker container started with privileged permissions",
    ]

def _gen_firewall(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [warning] kernel: [{cmd_word.upper()}] rule added to INPUT_chain by user",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=setsockopt family=inet protocol=NETFILTER",
    ]

def _gen_screen(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Terminal multiplexer session created",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=clone flags=CLONE_NEWPID|CLONE_NEWNS",
    ]

def _gen_sudo(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] sudo[{_rand_pid()}]: root : TTY=pts/{random.randint(0, 5)} ; USER=root ; COMMAND={command[:100]}",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=execve exe=/usr/bin/sudo",
    ]

def _gen_su(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] su[{_rand_pid()}]: session opened for user {random.choice(['root', 'www-data', 'postgres'])} by user",
        f"[{apache_ts()}] [info] pam_unix(su:session): session opened for user {random.choice(['root', 'www-data'])}",
    ]

def _gen_useradd(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(r'(?:useradd|adduser)\s+(\S+)', command)
    u = m.group(1) if m else "newuser"
    return [f"[{apache_ts()}] [warning] useradd[{_rand_pid()}]: new user: name={u}, uid={random.randint(2000, 9999)}"]

def _gen_passwd(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] passwd[{_rand_pid()}]: password changed for {random.choice(['root', 'admin', 'user'])}",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=setxattr op=security.selinux",
    ]

def _gen_analyze(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    target = random.choice(['/bin/ls', '/usr/bin/sshd', '/usr/sbin/apache2', '/bin/bash', '/usr/bin/python3'])
    return [
        f"[{apache_ts()}] [warning] [client {src}] Binary analysis tool {cmd_word} executed on {target}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}",
    ]

def _gen_crypto(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    op = random.choice(['genrsa', 'req -x509', 's_client', 's_server', 'enc', 'dgst'])
    return [
        f"[{apache_ts()}] [info] [client {src}] TLS/SSL operation: {op}",
        f"[{apache_ts()}] [warning] [client {src}] Certificate validation warning",
    ]

def _gen_compile(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    m = re.search(rf'{cmd_word}\s+(\S+)', command)
    f = m.group(1) if m else "payload.c"
    return [
        f"[{apache_ts()}] [info] [client {src}] Compilation started: {f}",
        f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}",
    ]

def _gen_nohup(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] Background process started (nohup)",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=clone flags=CLONE_VM|CLONE_VFORK",
    ]

def _gen_which(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [f"[{apache_ts()}] [info] [client {src}] Binary location queried via {cmd_word}"]

def _gen_default(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [error] [client {src}] File does not exist: /{technique.lower()}/payload",
        f"[{apache_ts()}] [error] [client {src}] POST /index.php HTTP/1.1\" 404 {random.randint(50, 500)}",
    ]

def _gen_any(command: str, cmd_word: str, technique: str) -> list[str]:
    src = _src_ip()
    return [
        f"[{apache_ts()}] [info] [client {src}] {cmd_word} execution detected",
        f"[{apache_ts()}] [info] auditd[{_rand_pid()}]: syscall=execve exe=/usr/bin/{cmd_word}",
    ]


_COMMAND_MAP: dict[str, CommandHandler] = {
    # Network scanning / connections
    "nmap": _gen_nmap,
    "nc": _gen_nc,
    "ncat": _gen_nc,
    "telnet": _gen_telnet,
    "ping": _gen_net_util,
    "netstat": _gen_net_util,
    "ss": _gen_net_util,
    "traceroute": _gen_net_util,
    "tracepath": _gen_net_util,
    "arp": _gen_net_util,
    "route": _gen_net_util,
    "tcpdump": _gen_packet_cap,
    "tshark": _gen_packet_cap,
    "tcpflow": _gen_packet_cap,
    # HTTP / downloads
    "curl": _gen_http,
    "wget": _gen_http,
    # SSH / remote
    "ssh": _gen_ssh,
    "scp": _gen_scp,
    "sftp": _gen_scp,
    # Scripting languages
    "python": _gen_script,
    "python2": _gen_script,
    "python3": _gen_script,
    "perl": _gen_script,
    "ruby": _gen_script,
    "php": _gen_script,
    "node": _gen_script,
    "nodejs": _gen_script,
    "bash": _gen_script,
    "sh": _gen_script,
    "zsh": _gen_script,
    "ksh": _gen_script,
    "fish": _gen_script,
    # Package managers
    "apt-get": _gen_pkg,
    "apt": _gen_pkg,
    "yum": _gen_pkg,
    "dnf": _gen_pkg,
    "dpkg": _gen_pkg,
    "pip": _gen_pkg,
    "pip3": _gen_pkg,
    "npm": _gen_pkg,
    "choco": _gen_pkg,
    "brew": _gen_pkg,
    "gem": _gen_pkg,
    "cargo": _gen_pkg,
    # Windows
    "powershell": _gen_powershell,
    "pwsh": _gen_powershell,
    "cmd": _gen_cmd,
    "cscript": _gen_win_script,
    "wscript": _gen_win_script,
    "reg": _gen_registry,
    "schtasks": _gen_schtasks,
    "wmic": _gen_wmic,
    "certutil": _gen_certutil,
    "bitsadmin": _gen_bitsadmin,
    "rundll32": _gen_rundll32,
    "mshta": _gen_mshta,
    "msiexec": _gen_msiexec,
    "net": _gen_net_windows,
    "net1": _gen_net_windows,
    "sc": _gen_service_windows,
    "vssadmin": _gen_vssadmin,
    "wevtutil": _gen_wevtutil,
    "bcdedit": _gen_bcdedit,
    # File read / view
    "cat": _gen_file_read,
    "head": _gen_file_read,
    "tail": _gen_file_read,
    "more": _gen_file_read,
    "less": _gen_file_read,
    "nl": _gen_file_read,
    "od": _gen_file_read,
    "xxd": _gen_file_read,
    "tac": _gen_file_read,
    "rev": _gen_file_read,
    # File write / modification
    "echo": _gen_echo,
    "touch": _gen_touch,
    "cp": _gen_cp,
    "mv": _gen_mv,
    "rm": _gen_rm,
    "tee": _gen_echo,
    "base64": _gen_base64,
    "dd": _gen_dd,
    "find": _gen_find,
    # Archive
    "tar": _gen_archive,
    "zip": _gen_archive,
    "unzip": _gen_archive,
    "gzip": _gen_archive,
    "gunzip": _gen_archive,
    "bzip2": _gen_archive,
    "bunzip2": _gen_archive,
    "xz": _gen_archive,
    "unxz": _gen_archive,
    "7z": _gen_archive,
    "7za": _gen_archive,
    # Text processing
    "grep": _gen_text_tool,
    "egrep": _gen_text_tool,
    "fgrep": _gen_text_tool,
    "sed": _gen_text_tool,
    "awk": _gen_text_tool,
    "sort": _gen_text_tool,
    "uniq": _gen_text_tool,
    "wc": _gen_text_tool,
    "cut": _gen_text_tool,
    "tr": _gen_text_tool,
    "diff": _gen_text_tool,
    "patch": _gen_text_tool,
    "comm": _gen_text_tool,
    "cmp": _gen_text_tool,
    # System info
    "whoami": _gen_whoami,
    "id": _gen_whoami,
    "who": _gen_whoami,
    "w": _gen_whoami,
    "hostname": _gen_sys_info,
    "uname": _gen_sys_info,
    "uptime": _gen_sys_info,
    "dnsdomainname": _gen_sys_info,
    "domainname": _gen_sys_info,
    # Network config
    "ifconfig": _gen_net_config,
    "ip": _gen_net_config,
    # Environment
    "env": _gen_env,
    "export": _gen_env,
    "set": _gen_env,
    "printenv": _gen_env,
    "declare": _gen_env,
    "typeset": _gen_env,
    "readonly": _gen_env,
    # Session
    "history": _gen_history,
    "clear": _gen_clear,
    "reset": _gen_clear,
    "alias": _gen_alias_mod,
    "unalias": _gen_alias_mod,
    # Process
    "ps": _gen_ps,
    "top": _gen_ps,
    "htop": _gen_ps,
    "pstree": _gen_ps,
    "kill": _gen_kill,
    "pkill": _gen_kill,
    "killall": _gen_kill,
    "skill": _gen_kill,
    # Services
    "systemctl": _gen_service,
    "service": _gen_service,
    "init": _gen_service,
    "rc-service": _gen_service,
    "supervisorctl": _gen_service,
    # Cron
    "crontab": _gen_cron,
    "at": _gen_cron,
    "atq": _gen_cron,
    "atrm": _gen_cron,
    "batch": _gen_cron,
    "anacron": _gen_cron,
    # Kernel
    "insmod": _gen_kmod,
    "modprobe": _gen_kmod,
    "modinfo": _gen_kmod,
    "kmod": _gen_kmod,
    "lsmod": _gen_kmod,
    "rmmod": _gen_kmod,
    "depmod": _gen_kmod,
    # Disk
    "mount": _gen_mount,
    "umount": _gen_mount,
    "fdisk": _gen_disk,
    "parted": _gen_disk,
    "mkfs": _gen_disk,
    "mkswap": _gen_disk,
    "swapon": _gen_disk,
    "swapoff": _gen_disk,
    "blkid": _gen_disk,
    "lsblk": _gen_disk,
    "df": _gen_disk,
    "du": _gen_disk,
    "fsck": _gen_disk,
    # Git
    "git": _gen_git,
    # Containers
    "docker": _gen_docker,
    "podman": _gen_docker,
    "nerdctl": _gen_docker,
    "containerd": _gen_docker,
    "ctr": _gen_docker,
    "docker-compose": _gen_docker,
    # Firewall
    "iptables": _gen_firewall,
    "ip6tables": _gen_firewall,
    "ufw": _gen_firewall,
    "firewall-cmd": _gen_firewall,
    "nft": _gen_firewall,
    "nftables": _gen_firewall,
    # Screen
    "screen": _gen_screen,
    "tmux": _gen_screen,
    "byobu": _gen_screen,
    # Privilege
    "sudo": _gen_sudo,
    "su": _gen_su,
    "doas": _gen_su,
    "runuser": _gen_su,
    # User management
    "useradd": _gen_useradd,
    "adduser": _gen_useradd,
    "usermod": _gen_useradd,
    "userdel": _gen_useradd,
    "deluser": _gen_useradd,
    "groupadd": _gen_useradd,
    "addgroup": _gen_useradd,
    "groupdel": _gen_useradd,
    "gpasswd": _gen_useradd,
    "passwd": _gen_passwd,
    "chpasswd": _gen_passwd,
    # Binary analysis
    "ldd": _gen_analyze,
    "strace": _gen_analyze,
    "ltrace": _gen_analyze,
    "objdump": _gen_analyze,
    "readelf": _gen_analyze,
    "nm": _gen_analyze,
    "strings": _gen_analyze,
    "file": _gen_analyze,
    # Crypto
    "openssl": _gen_crypto,
    "gpg": _gen_crypto,
    "gpg2": _gen_crypto,
    "keytool": _gen_crypto,
    # Compilation
    "make": _gen_compile,
    "gcc": _gen_compile,
    "g++": _gen_compile,
    "cc": _gen_compile,
    "clang": _gen_compile,
    "clang++": _gen_compile,
    "go": _gen_compile,
    "rustc": _gen_compile,
    # Background
    "nohup": _gen_nohup,
    "disown": _gen_nohup,
    # which / locate
    "which": _gen_which,
    "whereis": _gen_which,
    "locate": _gen_which,
    # Other
    "chmod": _gen_any,
    "chown": _gen_any,
    "chgrp": _gen_any,
    "ln": _gen_any,
    "mkdir": _gen_any,
    "rmdir": _gen_any,
    "mktemp": _gen_any,
    "readlink": _gen_any,
    "realpath": _gen_any,
    "dirname": _gen_any,
    "basename": _gen_any,
    "sleep": _gen_any,
    "true": _gen_any,
    "false": _gen_any,
    "yes": _gen_any,
    "seq": _gen_any,
    "expr": _gen_any,
    "time": _gen_any,
    "xargs": _gen_any,
    "date": _gen_any,
    "cal": _gen_any,
    "nproc": _gen_any,
    "getconf": _gen_any,
}

_TECHNIQUE_FALLBACK: list[tuple[re.Pattern, CommandHandler]] = [
    (re.compile(r"scan|discovery|reconnaissance|probe|detect", re.I), _gen_nmap),
    (re.compile(r"exploit|vulnerability|injection|overflow|deserialization", re.I), _gen_script),
    (re.compile(r"persistence|boot|startup|autorun|backdoor", re.I), _gen_service),
    (re.compile(r"credential|password|secrets|unsecured|dump|hash|kerberos", re.I), _gen_file_read),
    (re.compile(r"lateral|remote|movement|psexec|wmi|winrm", re.I), _gen_powershell),
    (re.compile(r"exfiltrat|collect|archive|compress|upload", re.I), _gen_archive),
    (re.compile(r"defense|bypass|disable|evasion|unload|stop.*(?:log|firewall|defender)", re.I), _gen_wevtutil),
    (re.compile(r"privilege|escalation|elevat|token|uac", re.I), _gen_sudo),
]


def generate_logs_for_test(technique: str, technique_name: str, test_name: str, command: str) -> list[str] | None:
    cmd_word = first_word(command)

    handler = _COMMAND_MAP.get(cmd_word)
    if handler:
        return handler(command, cmd_word, technique)

    combined = f"{technique_name} {test_name}"
    for pattern, handler in _TECHNIQUE_FALLBACK:
        if pattern.search(combined):
            return handler(command, cmd_word, technique)

    return None


def simulate_atomic_test(sink: OutputSink, config: SimulatorConfig, technique: str) -> None:
    start = datetime.now(timezone.utc)

    yaml_path = config.atomics_folder / technique / f"{technique}.yaml"
    if not yaml_path.exists():
        sink.write_line(f"[{apache_ts()}] [warning] [client 127.0.0.1] Atomic technique {technique} not found: {yaml_path}")
        return

    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        sink.write_line(f"[{apache_ts()}] [error] [client 127.0.0.1] Failed to parse {technique}.yaml: {exc}")
        return

    if not isinstance(data, dict):
        return

    technique_name = data.get("display_name") or technique
    atomic_tests = data.get("atomic_tests") or []
    generated_count = 0
    has_logs = False

    for test in atomic_tests[:3]:
        if not isinstance(test, dict):
            continue
        test_name = test.get("name", "unknown")
        executor = test.get("executor") or {}
        command = (executor.get("command") or "").strip()
        command_clean = re.sub(r'#\{[^}]+\}', '$param', command)

        log_lines = generate_logs_for_test(technique, technique_name, test_name, command_clean)
        if log_lines is not None:
            for line in log_lines:
                sink.write_line(line)
                generated_count += 1
            has_logs = True

    end = datetime.now(timezone.utc)

    if not has_logs:
        with config.unknown_file.open("a", encoding="utf-8") as f:
            f.write(f"{technique}\n")
        return

    timeline_line = "|".join([
        start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        technique,
    ]) + "\n"

    with config.timeline_file.open("a", encoding="utf-8") as tl:
        tl.write(timeline_line)

    if config.host_timeline_file:
        try:
            with config.host_timeline_file.open("a", encoding="utf-8") as htl:
                htl.write(timeline_line)
        except Exception:
            pass

    row = [
        start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        end.isoformat(timespec="seconds").replace("+00:00", "Z"),
        technique,
    ]
    with config.markers_file.open("a", encoding="utf-8", newline="") as mk:
        csv.writer(mk).writerow(row)

    if config.host_markers_file:
        try:
            with config.host_markers_file.open("a", encoding="utf-8", newline="") as hmk:
                csv.writer(hmk).writerow(row)
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


def clear_output_files(config: SimulatorConfig) -> None:
    for p in [config.log_file, config.timeline_file, config.markers_file]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("", encoding="utf-8")

    with config.markers_file.open("w", encoding="utf-8", newline="") as mk:
        csv.writer(mk).writerow(["timestamp_start", "timestamp_end", "technique"])

    host_files = [config.host_log_file, config.host_timeline_file, config.host_markers_file]
    for p in host_files:
        if p is None:
            continue
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
        except Exception:
            pass

    if config.host_markers_file:
        try:
            with config.host_markers_file.open("w", encoding="utf-8", newline="") as mk:
                csv.writer(mk).writerow(["timestamp_start", "timestamp_end", "technique"])
        except Exception:
            pass


def main() -> int:
    config = parse_config()
    validate_mode(config)

    clear_output_files(config)
    config.unknown_file.parent.mkdir(parents=True, exist_ok=True)

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
                simulate_atomic_test(sink, config, technique)

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
