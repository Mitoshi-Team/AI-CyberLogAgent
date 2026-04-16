#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

usage() {
  cat <<'EOF'
Usage:
  ./run.sh [command] [options]

Commands:
  start                       Start simulator (default)
  random                      Alias for start in random mode
  fixed [TECHNIQUE] [sec]     Start fixed mode (technique + optional interval)
  logs                        Follow container logs
  stop                        Stop and remove containers (alias: down)
  down                        Stop and remove containers
  help                        Show this help

Options:
  --random                      Run in random attack mode (default)
  --fixed <TECHNIQUE>           Run fixed MITRE technique (e.g. T1059)
  --interval <sec>              Interval for fixed mode (default: 90)
  --min <sec>                   Min random interval (default: 60)
  --max <sec>                   Max random interval (default: 120)
  --seed <n>                    Random seed (default: 42)
  --rate <n>                    Log rate per second (default: 200)
  --max-logs <n>                Stop after N emitted log lines (0 = unlimited)
  --host <name>                 Hostname in logs (default: target-node-01)
  --no-build                    Skip image rebuild
  --logs                        Follow logs only
  --down                        Stop and remove containers
  -h, --help                    Show this help

Examples:
  ./run.sh start
  ./run.sh fixed T1059 60
  ./run.sh --random --min 30 --max 45 --seed 123
  ./run.sh --logs
  ./run.sh stop
EOF
}

ATTACK_MODE="random"
FIXED_TECHNIQUE="T1059"
ATTACK_INTERVAL="90"
ATTACK_INTERVAL_MIN="60"
ATTACK_INTERVAL_MAX="120"
RANDOM_SEED="42"
LOG_RATE="200"
MAX_LOG_LINES="0"
HOSTNAME_OVERRIDE="target-node-01"
RESTART_POLICY="unless-stopped"
ACTION="up"
NO_BUILD="0"

# Optional short command as first argument.
if [[ $# -gt 0 ]]; then
  case "$1" in
    start)
      ACTION="up"
      shift
      ;;
    random)
      ACTION="up"
      ATTACK_MODE="random"
      shift
      ;;
    fixed)
      ACTION="up"
      ATTACK_MODE="fixed"
      shift

      if [[ $# -gt 0 && "$1" != --* ]]; then
        FIXED_TECHNIQUE="$1"
        shift
      fi
      if [[ $# -gt 0 && "$1" != --* ]]; then
        ATTACK_INTERVAL="$1"
        shift
      fi
      ;;
    logs)
      ACTION="logs"
      shift
      ;;
    stop|down)
      ACTION="down"
      shift
      ;;
    help)
      usage
      exit 0
      ;;
  esac
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --random)
      ATTACK_MODE="random"
      shift
      ;;
    --fixed)
      ATTACK_MODE="fixed"
      FIXED_TECHNIQUE="${2:-}"
      if [[ -z "${FIXED_TECHNIQUE}" ]]; then
        echo "Error: --fixed requires a technique, e.g. --fixed T1059"
        exit 1
      fi
      shift 2
      ;;
    --interval)
      ATTACK_INTERVAL="${2:-}"
      [[ -n "${ATTACK_INTERVAL}" ]] || { echo "Error: --interval requires value"; exit 1; }
      shift 2
      ;;
    --min)
      ATTACK_INTERVAL_MIN="${2:-}"
      [[ -n "${ATTACK_INTERVAL_MIN}" ]] || { echo "Error: --min requires value"; exit 1; }
      shift 2
      ;;
    --max)
      ATTACK_INTERVAL_MAX="${2:-}"
      [[ -n "${ATTACK_INTERVAL_MAX}" ]] || { echo "Error: --max requires value"; exit 1; }
      shift 2
      ;;
    --seed)
      RANDOM_SEED="${2:-}"
      [[ -n "${RANDOM_SEED}" ]] || { echo "Error: --seed requires value"; exit 1; }
      shift 2
      ;;
    --rate)
      LOG_RATE="${2:-}"
      [[ -n "${LOG_RATE}" ]] || { echo "Error: --rate requires value"; exit 1; }
      shift 2
      ;;
    --max-logs)
      MAX_LOG_LINES="${2:-}"
      [[ -n "${MAX_LOG_LINES}" ]] || { echo "Error: --max-logs requires value"; exit 1; }
      shift 2
      ;;
    --host)
      HOSTNAME_OVERRIDE="${2:-}"
      [[ -n "${HOSTNAME_OVERRIDE}" ]] || { echo "Error: --host requires value"; exit 1; }
      shift 2
      ;;
    --no-build)
      NO_BUILD="1"
      shift
      ;;
    --logs)
      ACTION="logs"
      shift
      ;;
    --down)
      ACTION="down"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if command -v docker >/dev/null 2>&1; then
  :
else
  echo "Docker is not installed or not in PATH"
  exit 1
fi

compose_cmd=(docker compose)
if docker compose version >/dev/null 2>&1; then
  :
elif command -v docker-compose >/dev/null 2>&1; then
  compose_cmd=(docker-compose)
else
  echo "Neither 'docker compose' nor 'docker-compose' is available"
  exit 1
fi

case "${ACTION}" in
  down)
    "${compose_cmd[@]}" down --remove-orphans
    exit 0
    ;;
  logs)
    "${compose_cmd[@]}" logs -f mitre-log-simulator
    exit 0
    ;;
esac

cmd=("${compose_cmd[@]}" up --remove-orphans)
if [[ "${NO_BUILD}" != "1" ]]; then
  cmd+=(--build)
fi

ATTACK_MODE="${ATTACK_MODE}" \
FIXED_TECHNIQUE="${FIXED_TECHNIQUE}" \
ATTACK_INTERVAL="${ATTACK_INTERVAL}" \
ATTACK_INTERVAL_MIN="${ATTACK_INTERVAL_MIN}" \
ATTACK_INTERVAL_MAX="${ATTACK_INTERVAL_MAX}" \
RANDOM_SEED="${RANDOM_SEED}" \
LOG_RATE="${LOG_RATE}" \
MAX_LOG_LINES="${MAX_LOG_LINES}" \
RESTART_POLICY="$([ "${MAX_LOG_LINES}" -gt 0 ] && echo "no" || echo "${RESTART_POLICY}")" \
HOSTNAME_OVERRIDE="${HOSTNAME_OVERRIDE}" \
"${cmd[@]}"
