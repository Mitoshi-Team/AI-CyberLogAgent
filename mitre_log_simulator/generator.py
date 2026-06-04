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


def generate_logs_for_test(technique: str, test_name: str, command: str) -> list[str]:
    lines: list[str] = []
    now = datetime.now(timezone.utc)
    base = apache_ts(now)
    src = f"10.0.{random.randint(0, 255)}.{random.randint(2, 254)}"
    cmd = command.lower()

    if re.search(r'\bcurl\s', cmd):
        url_m = re.search(r'https?://([^\s\'"]+)', command)
        url = url_m.group(1) if url_m else f"{src}/payload"
        fn = url.rsplit("/", 1)[-1] if "/" in url else "index.html"
        lines.append(f"[{base}] [error] [client {src}] File does not exist: /{fn}, referer: http://{url}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 5000)} \"-\" \"curl/7.81.0\"")

    elif re.search(r'\bwget\s', cmd):
        url_m = re.search(r'https?://([^\s\'"]+)', command)
        url = url_m.group(1) if url_m else f"{src}/payload"
        lines.append(f"[{base}] [error] [client {src}] File does not exist: /download, referer: http://{url}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)} \"-\" \"Wget/1.21.3\"")

    elif re.search(r'\bnmap\b', cmd):
        t = f"10.0.{random.randint(0, 255)}.0/24"
        lines.append(f"[{base}] [warning] [client {src}] Possible SYN flood detected from {src}")
        lines.append(f"[{apache_ts()}] [error] [client {src}] Connection attempt to {t.split('/')[0]}.{random.randint(2, 254)} port {random.choice([22, 80, 443, 8080, 8443])} rejected")

    elif re.search(r'\bnc\b', cmd) or re.search(r'\bncat\b', cmd):
        host_m = re.search(r'nc\s+(-[a-z]+\s+)?(\S+)\s+(\d+)', cmd)
        if host_m:
            lines.append(f"[{base}] [warning] [client {src}] Outbound raw connection to {host_m.group(2)}:{host_m.group(3)}")
        else:
            lines.append(f"[{base}] [warning] [client {src}] Outbound raw connection to external host")

    elif re.search(r'\bchmod\s+\+?x?\b', cmd) and re.search(r'(?:/tmp|/dev/shm|/var/tmp)', cmd):
        p_m = re.search(r'chmod\s+\+?x?\s+(\S+)', command)
        p = p_m.group(1) if p_m else "/tmp/file"
        lines.append(f"[{base}] [notice] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(100, 500)}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=chmod path={p}")

    elif re.search(r'base64\s+(-d|--decode|-D)', cmd):
        lines.append(f"[{base}] [notice] [client {src}] POST /upload.cgi HTTP/1.1\" 200 {random.randint(200, 500)}")
        lines.append(f"[{apache_ts()}] [error] [client {src}] Premature end of script headers: /cgi-bin/upload.cgi")

    elif re.search(r'(?<!\w)ssh\s+', cmd):
        u_m = re.search(r'ssh\s+(\w+)@', cmd)
        h_m = re.search(r'ssh\s+(?:\w+@)?(\S+)', cmd)
        u = u_m.group(1) if u_m else "root"
        h = h_m.group(1) if h_m else f"10.0.{random.randint(0, 255)}.{random.randint(2, 254)}"
        lines.append(f"[{base}] [info] sshd[{random.randint(1000, 9999)}]: Accepted publickey for {u} from {h} port {random.randint(10000, 65000)}")
        lines.append(f"[{apache_ts()}] [info] sshd[{random.randint(1000, 9999)}]: pam_unix(sshd:session): session opened for user {u} (uid={random.randint(1000, 9999)})")

    elif re.search(r'\bscp\b', cmd):
        lines.append(f"[{base}] [info] sshd[{random.randint(1000, 9999)}]: Received disconnect from {src}: 11: disconnected by user")
        lines.append(f"[{apache_ts()}] [info] sftp-server[{random.randint(1000, 9999)}]: session opened for local user")

    elif re.search(r'\biptables\b', cmd) or re.search(r'\bufw\b', cmd):
        lines.append(f"[{base}] [warning] kernel: [IPTABLES] rule added to INPUT_chain by user")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=setsockopt family=inet protocol=NETFILTER")

    elif re.search(r'\b(apt-get|yum|dnf|apt)\b', cmd):
        p_m = re.search(r'(?:install|remove)\s+(\S+)', cmd)
        p = p_m.group(1) if p_m else "package"
        lines.append(f"[{base}] [info] dpkg[{random.randint(1000, 9999)}]: {p}:amd64 installed")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}")

    elif re.search(r'\bpip\b', cmd) and re.search(r'install', cmd):
        p_m = re.search(r'pip(?:\d+\.?\d*)?\s+install\s+(\S+)', cmd)
        p = p_m.group(1) if p_m else "package"
        lines.append(f"[{base}] [info] pip[{random.randint(1000, 9999)}]: installed {p} (Python {random.choice([3.8, 3.9, 3.10, 3.11, 3.12])})")
        lines.append(f"[{apache_ts()}] [notice] [client {src}] POST / HTTP/1.1\" 200 {random.randint(100, 500)}")

    elif re.search(r'\bdocker\b', cmd):
        lines.append(f"[{base}] [notice] [client {src}] Docker API: POST /containers/create HTTP/1.1")
        lines.append(f"[{apache_ts()}] [error] [client {src}] Docker container started with --privileged flag")

    elif re.search(r'\bgit\s+clone\b', cmd):
        r_m = re.search(r'clone\s+(\S+)', cmd)
        r = r_m.group(1) if r_m else "repository"
        lines.append(f"[{base}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)} \"-\" \"git/2.34.1\"")
        lines.append(f"[{apache_ts()}] [info] [client {src}] Repository cloned: {r.split('/')[-1].replace('.git', '')}")

    elif re.search(r'\bpython\s+-[ce]\b', cmd) or re.search(r'\bperl\s+-e\b', cmd) or re.search(r'\bruby\s+-e\b', cmd):
        lines.append(f"[{base}] [error] [client {src}] POST /cgi-bin/exec.cgi HTTP/1.1\" 500 {random.randint(50, 200)}")
        lines.append(f"[{apache_ts()}] [error] [client {src}] Script execution failed with exit code {random.choice([1, 2, 126, 127, 255])}")

    elif re.search(r'/etc/passwd', cmd) or re.search(r'/etc/shadow', cmd) or re.search(r'/etc/group', cmd):
        lines.append(f"[{base}] [error] [client {src}] File does not exist: /etc/passwd")
        lines.append(f"[{apache_ts()}] [error] [client {src}] Client denied by server configuration: /etc/shadow")

    elif re.search(r'/proc/', cmd):
        lines.append(f"[{base}] [warning] [client {src}] Process enumeration via /proc/{random.choice(['cpuinfo', 'meminfo', 'self/status', 'net/tcp', 'self/maps'])}")

    elif re.search(r'(?<!\w)ls\s+-la\s+/\b', cmd) or re.search(r'\bfind\s+/\b', cmd):
        lines.append(f"[{base}] [notice] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(100, 500)}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=getdents64 cwd=/")

    elif re.search(r'\b(whoami|id|who|w)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(50, 500)}")

    elif re.search(r'\btelnet\b', cmd):
        h_m = re.search(r'telnet\s+(\S+)', cmd)
        h = h_m.group(1) if h_m else "external-host"
        lines.append(f"[{base}] [warning] telnet[{random.randint(1000, 9999)}]: connect from {src} to {h}:23")
        lines.append(f"[{apache_ts()}] [info] telnetd[{random.randint(1000, 9999)}]: login from {src}")

    elif re.search(r'\becho\b.*[>]', cmd):
        f_m = re.search(r'>\s*(\S+)', command)
        f = f_m.group(1) if f_m else "/tmp/file"
        lines.append(f"[{base}] [error] [client {src}] File created: {f}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(500, 5000)}")

    elif re.search(r'\btouch\b', cmd):
        f_m = re.search(r'touch\s+(\S+)', command)
        f = f_m.group(1) if f_m else "/tmp/file"
        lines.append(f"[{base}] [notice] [client {src}] File timestamp modified: {f}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=utimensat path={f}")

    elif re.search(r'\bkill\b', cmd):
        pid_m = re.search(r'kill\s+-?\d*\s+(\d+)', cmd)
        pid = pid_m.group(1) if pid_m else str(random.randint(1000, 9999))
        lines.append(f"[{base}] [warning] kernel: process {pid} received SIG{random.choice(['TERM', 'KILL', 'HUP', 'INT'])}")
        lines.append(f"[{apache_ts()}] [info] systemd[{random.randint(1, 999)}]: Unit process-{pid}.scope: Deactivated successfully")

    elif re.search(r'\bsystemctl\b', cmd) or re.search(r'\bservice\b', cmd):
        lines.append(f"[{base}] [info] systemd[{random.randint(1, 999)}]: Stopped {random.choice(['nginx.service', 'apache2.service', 'sshd.service', 'mysql.service'])}")
        lines.append(f"[{apache_ts()}] [info] systemd[{random.randint(1, 999)}]: Started {random.choice(['nginx.service', 'apache2.service', 'sshd.service', 'mysql.service'])}")

    elif re.search(r'\bcrontab\b', cmd):
        lines.append(f"[{base}] [warning] crontab[{random.randint(1000, 9999)}]: REPLACE (user)")
        lines.append(f"[{apache_ts()}] [info] cron[{random.randint(1000, 9999)}]: (user) CMD (/bin/sh -c \"...\")")

    elif re.search(r'\bopenssl\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] TLS certificate operation: {random.choice(['genrsa', 'req', 'x509', 's_client', 's_server'])}")

    elif re.search(r'\bmount\b', cmd):
        lines.append(f"[{base}] [notice] kernel: EXT4-fs ({random.choice(['sda1', 'sdb1', 'nvme0n1p1', 'xvd1'])}): mounted filesystem")
        lines.append(f"[{apache_ts()}] [info] [client {src}] Filesystem mounted with {random.choice(['exec', 'suid', 'dev'])} permissions")

    elif re.search(r'\b(useradd|adduser)\b', cmd):
        u_m = re.search(r'(?:useradd|adduser)\s+(\S+)', command)
        u = u_m.group(1) if u_m else "newuser"
        lines.append(f"[{base}] [warning] useradd[{random.randint(1000, 9999)}]: new user: name={u}, uid={random.randint(2000, 9999)}, gid={random.randint(2000, 9999)}, shell=/bin/bash")

    elif re.search(r'(?<!\w)passwd\b', cmd):
        lines.append(f"[{base}] [info] passwd[{random.randint(1000, 9999)}]: password changed for {random.choice(['root', 'admin', 'user'])}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=setxattr op=security.selinux")

    elif re.search(r'\bsudo\b', cmd):
        c_t = cmd[:100]
        lines.append(f"[{base}] [info] sudo[{random.randint(1000, 9999)}]: root : TTY=pts/{random.randint(0, 5)} ; USER=root ; COMMAND={c_t}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=execve exe=/usr/bin/sudo")

    elif re.search(r'\b(export|env|set)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Environment variables accessed by user")
        lines.append(f"[{apache_ts()}] [notice] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}")

    elif re.search(r'\bps\s+(?:aux|-ef|ax)\b', cmd) or re.search(r'\btop\b', cmd):
        lines.append(f"[{base}] [notice] [client {src}] Process listing requested by user")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}")

    elif re.search(r'\b(ifconfig|ip\s+addr)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Network configuration queried by user")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 1000)}")

    elif re.search(r'\b(sed|awk|grep)\b', cmd):
        lines.append(f"[{base}] [notice] [client {src}] File content search performed on {random.choice(['/var/log', '/etc', '/home', '/tmp'])}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=openat flags=O_RDONLY")

    elif re.search(r'\b(make|gcc|g\+\+|cc)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Compilation started: {random.choice(['exploit.c', 'payload.c', 'shellcode.c', 'bypass.c'])}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}")

    elif re.search(r'\bnohup\b', cmd) or re.search(r'\bdisown\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Background process started (nohup)")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=clone flags=CLONE_VM|CLONE_VFORK")

    elif re.search(r'\b(uname|hostname|dnsdomainname)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] System information queried")

    elif re.search(r'\b(dd|fdisk|mkfs|parted)\b', cmd):
        lines.append(f"[{base}] [warning] kernel: I/O error on device {random.choice(['sda', 'sdb', 'nvme0n1', 'md0'])}, logical block {random.randint(0, 9999)}")
        lines.append(f"[{apache_ts()}] [notice] [client {src}] Disk manipulation tool executed")

    elif re.search(r'\b(tshark|tcpdump|tcpflow)\b', cmd):
        lines.append(f"[{base}] [warning] [client {src}] Network packet capture started on interface {random.choice(['eth0', 'ens33', 'enp0s3'])}")

    elif re.search(r'\b(insmod|modprobe|kmod)\b', cmd):
        lines.append(f"[{base}] [warning] kernel: {random.choice(['sctp', 'raw', 'af_key', 'tun'])}: module loaded from {src}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] Kernel module loaded by user")

    elif re.search(r'\b(screen|tmux)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Terminal multiplexer session created")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=clone flags=CLONE_NEWPID|CLONE_NEWNS")

    elif re.search(r'\b(openssl|keytool|certutil)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Certificate operation: {random.choice(['export', 'import', 'generate', 'sign'])}")
        lines.append(f"[{apache_ts()}] [warning] [client {src}] TLS certificate validation warning: self-signed certificate")

    elif re.search(r'\b(tee|cat)\b.*>', cmd) or re.search(r'\b>\s*(?:>>)?\s*/', cmd):
        f_m = re.search(r'>\s*(\S+)', command)
        f = f_m.group(1) if f_m else "/tmp/file"
        lines.append(f"[{base}] [error] [client {src}] File created: {f}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] POST /index.php HTTP/1.1\" 200 {random.randint(500, 5000)}")

    elif re.search(r'\bcp\s+', cmd) and re.search(r'(?:/tmp|/dev/shm|/var/tmp)', cmd):
        f_m = re.search(r'cp\s+(\S+)', command)
        f = f_m.group(1) if f_m else "file"
        lines.append(f"[{base}] [notice] [client {src}] File copied to temporary directory: {f}")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=sendfile")

    elif re.search(r'\bmv\s+', cmd) and re.search(r'(?:/tmp|/dev/shm|/var/tmp)', cmd):
        lines.append(f"[{base}] [notice] [client {src}] File moved to temporary location")

    elif re.search(r'\brm\s+(-rf\s+)?/', cmd) or re.search(r'\brm\s+(-rf\s+)?\*', cmd):
        lines.append(f"[{base}] [error] [client {src}] Mass file deletion detected on filesystem")
        lines.append(f"[{apache_ts()}] [warning] auditd[{random.randint(1000, 9999)}]: syscall=unlinkat count={random.randint(10, 999)}")

    elif re.search(r'\bhistory\b', cmd) or re.search(r'\bhistory\s+-c\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Command history cleared")

    elif re.search(r'\b(clear|reset)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Terminal session cleared")

    elif re.search(r'\b(alias|unalias)\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Shell alias modified")

    elif re.search(r'\b(cat|head|tail|more|less|nl|od|xxd)\s', cmd):
        lines.append(f"[{base}] [notice] [client {src}] File content viewed by user")
        lines.append(f"[{apache_ts()}] [info] auditd[{random.randint(1000, 9999)}]: syscall=read")

    elif re.search(r'\b(sort|uniq|wc|cut|tr|diff|patch)\b', cmd):
        lines.append(f"[{base}] [notice] [client {src}] File manipulation by user")

    elif re.search(r'\breadlink|which\s+|whereis\s+|command\s+-v\b', cmd):
        lines.append(f"[{base}] [info] [client {src}] Binary location queried")

    elif re.search(r'\b(ldd|strace|ltrace|objdump|readelf|nm)\s', cmd):
        lines.append(f"[{base}] [warning] [client {src}] Binary analysis tool executed on {random.choice(['/bin/ls', '/usr/bin/sshd', '/usr/sbin/apache2', '/bin/bash'])}")
        lines.append(f"[{apache_ts()}] [info] [client {src}] GET / HTTP/1.1\" 200 {random.randint(100, 500)}")

    else:
        lines.append(f"[{base}] [error] [client {src}] File does not exist: /{technique.lower()}/payload")
        lines.append(f"[{apache_ts()}] [error] [client {src}] POST /index.php HTTP/1.1\" 404 {random.randint(50, 500)}")

    for i in range(len(lines)):
        ts = apache_ts()
        match = re.match(r'^(\[[^\]]+\])', lines[i])
        if match:
            lines[i] = f"[{ts}]" + lines[i][len(match.group(0)):]

    return lines


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

    for test in atomic_tests[:3]:
        if not isinstance(test, dict):
            continue
        test_name = test.get("name", "unknown")
        executor = test.get("executor") or {}
        command = (executor.get("command") or "").strip()
        command_clean = re.sub(r'#\{[^}]+\}', '$param', command)

        log_lines = generate_logs_for_test(technique, test_name, command_clean)
        for line in log_lines:
            sink.write_line(line)
            generated_count += 1

    end = datetime.now(timezone.utc)

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
