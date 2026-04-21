#!/usr/bin/env bash
set -Eeuo pipefail

ORCHESTRATOR_PID_FILE="/tmp/orchestrator.pid"
LAST_STDOUT_TS_FILE="/tmp/last_stdout_ts"
UNHEALTHY_FLAG_FILE="/tmp/unhealthy"
STOP_REQUEST_FILE="/tmp/stop_requested"
SIM_SYSLOG_FILE="/tmp/syslog_sim.log"
GOLDEN_LOG_FILE="/var/log/golden/attack_timeline.log"
STREAM_LOG_FILE="/var/log/golden/simulator_stream.log"

ATTACK_MODE="${ATTACK_MODE:-random}"
FIXED_TECHNIQUE="${FIXED_TECHNIQUE:-T1059}"
ATTACK_INTERVAL="${ATTACK_INTERVAL:-90}"
ATTACK_INTERVAL_MIN="${ATTACK_INTERVAL_MIN:-60}"
ATTACK_INTERVAL_MAX="${ATTACK_INTERVAL_MAX:-120}"
LOG_RATE="${LOG_RATE:-200}"
RANDOM_SEED="${RANDOM_SEED:-42}"
HOSTNAME_OVERRIDE="${HOSTNAME_OVERRIDE:-target-node-01}"
FLOG_RPS="${FLOG_RPS:-5}"
MAX_LOG_LINES="${MAX_LOG_LINES:-0}"

LOG_LINES_EMITTED=0

# Allowed MITRE techniques for simulation only.
TECHNIQUES=(
  "T1059"
  "T1003"
  "T1547"
  "T1053"
  "T1136"
  "T1027"
  "T1082"
  "T1046"
  "T1070"
  "T1566"
)

flog_pid=""
main_pid=""

iso_now() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

epoch_now() {
  date +%s
}

emit_stdout() {
  local line="$1"

  # Stop emitting immediately once stop was requested.
  if [[ -f "${STOP_REQUEST_FILE}" ]]; then
    return 0
  fi

  echo "${line}"
  echo "${line}" >> "${STREAM_LOG_FILE}"
  epoch_now > "${LAST_STDOUT_TS_FILE}"

  LOG_LINES_EMITTED=$((LOG_LINES_EMITTED + 1))
  if (( MAX_LOG_LINES > 0 && LOG_LINES_EMITTED >= MAX_LOG_LINES )); then
    # Create stop marker atomically and announce the limit only once.
    if ( set -o noclobber; echo "1" > "${STOP_REQUEST_FILE}" ) 2>/dev/null; then
      echo "$(iso_now) app {\"level\":\"INFO\",\"msg\":\"Max log limit reached\",\"max_logs\":${MAX_LOG_LINES}}"
    fi
  fi
}

emit_syslog_like() {
  local facility="$1"
  local message="$2"
  local ts
  ts="$(iso_now)"
  local line="${ts} syslog ${facility}: ${message}"
  echo "${line}" >> "${SIM_SYSLOG_FILE}"
  emit_stdout "${line}"
}

validate_env() {
  case "${ATTACK_MODE}" in
    random|fixed) ;;
    *)
      emit_stdout "$(iso_now) app {\"level\":\"ERROR\",\"msg\":\"Invalid ATTACK_MODE\",\"value\":\"${ATTACK_MODE}\"}"
      exit 1
      ;;
  esac

  if [[ "${ATTACK_MODE}" == "fixed" ]]; then
    local ok="0"
    local t
    for t in "${TECHNIQUES[@]}"; do
      if [[ "${FIXED_TECHNIQUE}" == "${t}" ]]; then
        ok="1"
        break
      fi
    done
    if [[ "${ok}" != "1" ]]; then
      emit_stdout "$(iso_now) app {\"level\":\"ERROR\",\"msg\":\"FIXED_TECHNIQUE is not supported\",\"value\":\"${FIXED_TECHNIQUE}\"}"
      exit 1
    fi
  fi

  if ! [[ "${MAX_LOG_LINES}" =~ ^[0-9]+$ ]]; then
    emit_stdout "$(iso_now) app {\"level\":\"ERROR\",\"msg\":\"MAX_LOG_LINES must be integer >= 0\",\"value\":\"${MAX_LOG_LINES}\"}"
    exit 1
  fi
}

start_flog_noise() {
  (
    while true; do
      local line
      if line="$(flog -n 1 2>/dev/null | head -n 1)"; then
        emit_stdout "$(iso_now) nginx_access ${line}"
      else
        emit_stdout "$(iso_now) nginx_access 10.0.0.$((RANDOM % 255)) - - \"GET /health HTTP/1.1\" 200 $((RANDOM % 2048 + 128))"
      fi
      sleep 0.2
    done
  ) &
  flog_pid="$!"
}

random_json_level() {
  local levels=("INFO" "WARN" "ERROR")
  echo "${levels[$((RANDOM % ${#levels[@]}))]}"
}

generate_noise_line() {
  local source_id="$1"
  local ts
  ts="$(iso_now)"

  case "${source_id}" in
    0)
      emit_stdout "${ts} nginx_access 192.168.1.$((RANDOM % 255)) - - \"GET /api/v1/items/$((RANDOM % 1000)) HTTP/1.1\" 200 $((RANDOM % 4096 + 128))"
      ;;
    1)
      emit_stdout "${ts} nginx_error [error] $((RANDOM % 9000 + 1000))#0: *$((RANDOM % 10000)) upstream timed out while reading response header"
      ;;
    2)
      emit_stdout "${ts} postgres connection authorized: user=app_user db=orders client=10.20.0.$((RANDOM % 255))"
      ;;
    3)
      emit_stdout "${ts} postgres query duration=$((RANDOM % 950 + 50))ms statement=SELECT * FROM orders WHERE id=$((RANDOM % 100000));"
      ;;
    4)
      emit_syslog_like "auth" "Accepted password for service_user from 10.10.0.$((RANDOM % 255)) port $((RANDOM % 40000 + 2000)) ssh2"
      ;;
    5)
      emit_syslog_like "cron" "(root) CMD (/usr/local/bin/rotate_logs --tenant $((RANDOM % 12 + 1)))"
      ;;
    6)
      emit_syslog_like "kernel" "eth0: link up, tx_queue_len=1000, mtu=1500"
      ;;
    *)
      emit_stdout "${ts} app {\"level\":\"$(random_json_level)\",\"service\":\"payments\",\"msg\":\"request handled\",\"user\":\"user_$((RANDOM % 500))\",\"status\":$((RANDOM % 3 == 0 ? 500 : 200)),\"latency_ms\":$((RANDOM % 900 + 20))}"
      ;;
  esac
}

run_noise_batch() {
  local base_rate
  base_rate="${LOG_RATE}"

  local jitter=$(( base_rate / 10 ))
  local min_rate=$(( base_rate - jitter ))
  local max_rate=$(( base_rate + jitter ))

  if (( min_rate < 1 )); then
    min_rate=1
  fi

  # Keep total output around LOG_RATE (+-10%), including background flog stream.
  local min_budget=$(( min_rate - FLOG_RPS ))
  local max_budget=$(( max_rate - FLOG_RPS ))
  if (( min_budget < 1 )); then
    min_budget=1
  fi
  if (( max_budget < min_budget )); then
    max_budget=${min_budget}
  fi

  local count=$(( RANDOM % (max_budget - min_budget + 1) + min_budget ))
  local i

  for ((i=0; i<count; i++)); do
    generate_noise_line "$((RANDOM % 8))"
  done
}

safe_touch_marker() {
  local technique="$1"
  local ts="$2"
  local marker="/tmp/attack_${technique}_${ts}"
  echo "simulated_attack_marker" > "${marker}"
  echo "${marker}"
}

simulate_T1059() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1059" "${ts}")"
  emit_stdout "$(iso_now) [T1059] Simulated execution: bash -c 'echo reconnaissance && whoami' marker=${marker}"
}

simulate_T1003() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1003" "${ts}")"
  echo 'fake_hash_dump:root:$6$simulated' > "/tmp/fake_credential_dump_${ts}.txt"
  emit_stdout "$(iso_now) [T1003] Simulated execution: read fake credential material from /tmp/fake_credential_dump_${ts}.txt marker=${marker}"
}

simulate_T1547() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1547" "${ts}")"
  echo "@reboot /tmp/sim_autostart_${ts}.sh" > "/tmp/sim_crontab_${ts}.conf"
  emit_stdout "$(iso_now) [T1547] Simulated execution: created autostart config /tmp/sim_crontab_${ts}.conf marker=${marker}"
}

simulate_T1053() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1053" "${ts}")"
  echo "*/5 * * * * /tmp/sim_task_${ts}.sh" > "/tmp/sim_scheduled_task_${ts}.cron"
  emit_stdout "$(iso_now) [T1053] Simulated execution: scheduled task definition in /tmp/sim_scheduled_task_${ts}.cron marker=${marker}"
}

simulate_T1136() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1136" "${ts}")"
  echo "username=svc_backup_${ts}" > "/tmp/sim_account_${ts}.txt"
  emit_stdout "$(iso_now) [T1136] Simulated execution: account creation intent logged in /tmp/sim_account_${ts}.txt marker=${marker}"
}

simulate_T1027() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1027" "${ts}")"
  local payload="sensitive-content-${ts}"
  echo -n "${payload}" | base64 > "/tmp/sim_obfuscated_${ts}.b64"
  emit_stdout "$(iso_now) [T1027] Simulated execution: obfuscated payload to /tmp/sim_obfuscated_${ts}.b64 marker=${marker}"
}

simulate_T1082() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1082" "${ts}")"
  uname -a > "/tmp/sim_sysinfo_${ts}.txt"
  emit_stdout "$(iso_now) [T1082] Simulated execution: system discovery output in /tmp/sim_sysinfo_${ts}.txt marker=${marker}"
}

simulate_T1046() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1046" "${ts}")"
  local p
  for p in 22 80 443 5432; do
    # Echo-only network action to avoid real scanning.
    nc -z -w 1 127.0.0.1 "${p}" >/dev/null 2>&1 || true
    echo "probe 127.0.0.1:${p}" >> "/tmp/sim_scan_${ts}.log"
  done
  emit_stdout "$(iso_now) [T1046] Simulated execution: local echo probes recorded in /tmp/sim_scan_${ts}.log marker=${marker}"
}

simulate_T1070() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1070" "${ts}")"
  echo "pretend to clear logs" > "/tmp/sim_log_wipe_${ts}.txt"
  emit_stdout "$(iso_now) [T1070] Simulated execution: indicator removal intent in /tmp/sim_log_wipe_${ts}.txt marker=${marker}"
}

simulate_T1566() {
  local ts="$1"
  local marker
  marker="$(safe_touch_marker "T1566" "${ts}")"
  emit_stdout "$(iso_now) [T1566] Simulated execution: phishing email queued from=helpdesk@corp.local to=user$((RANDOM % 100))@corp.local subject='Password reset required' marker=${marker}"
}

run_technique() {
  local technique="$1"
  local start_ts
  local end_ts
  start_ts="$(iso_now)"

  emit_stdout "${start_ts} [TEST_START] Running ${technique}"

  case "${technique}" in
    T1059) simulate_T1059 "$(epoch_now)" ;;
    T1003) simulate_T1003 "$(epoch_now)" ;;
    T1547) simulate_T1547 "$(epoch_now)" ;;
    T1053) simulate_T1053 "$(epoch_now)" ;;
    T1136) simulate_T1136 "$(epoch_now)" ;;
    T1027) simulate_T1027 "$(epoch_now)" ;;
    T1082) simulate_T1082 "$(epoch_now)" ;;
    T1046) simulate_T1046 "$(epoch_now)" ;;
    T1070) simulate_T1070 "$(epoch_now)" ;;
    T1566) simulate_T1566 "$(epoch_now)" ;;
    *)
      emit_stdout "$(iso_now) app {\"level\":\"ERROR\",\"msg\":\"Unsupported technique\",\"technique\":\"${technique}\"}"
      return 1
      ;;
  esac

  local cleanup_status
  if perform_cleanup; then
    cleanup_status="CLEANUP_OK"
  else
    cleanup_status="CLEANUP_FAIL"
  fi

  end_ts="$(iso_now)"
  emit_stdout "${end_ts} [TEST_END] ${technique} status=${cleanup_status}"
  mkdir -p "$(dirname "${GOLDEN_LOG_FILE}")"
  echo "${end_ts}|${technique}|${start_ts}|${end_ts}|${cleanup_status}" >> "${GOLDEN_LOG_FILE}"

  if [[ "${cleanup_status}" == "CLEANUP_FAIL" ]]; then
    echo "1" > "${UNHEALTHY_FLAG_FILE}"
    emit_stdout "$(iso_now) app {\"level\":\"ERROR\",\"msg\":\"Cleanup failed, exiting for restart\"}"
    exit 1
  fi
}

perform_cleanup() {
  local ok=1

  # 1) Remove temporary simulation files in /tmp.
  rm -f /tmp/attack_T* /tmp/fake_credential_dump_*.txt /tmp/sim_* 2>/dev/null || ok=0

  # 2) Restore original configs if backups exist (simulated backup paths only in /tmp).
  if compgen -G "/tmp/config_backup_*.bak" > /dev/null; then
    local b
    for b in /tmp/config_backup_*.bak; do
      local restored="${b%.bak}"
      cp -f "${b}" "${restored}" 2>/dev/null || ok=0
      rm -f "${b}" 2>/dev/null || true
    done
  fi

  # 3) Ensure no suspicious simulation processes remain.
  if pgrep -f "sim_attack_worker" >/dev/null 2>&1; then
    pkill -f "sim_attack_worker" >/dev/null 2>&1 || ok=0
  fi

  # 4) Ensure simulated syslog does not contain cleanup errors.
  if [[ -f "${SIM_SYSLOG_FILE}" ]] && grep -q "CLEANUP_ERROR" "${SIM_SYSLOG_FILE}"; then
    ok=0
  fi

  if [[ "${ok}" -eq 1 ]]; then
    emit_stdout "$(iso_now) [CLEANUP_OK] All simulated artifacts removed"
    return 0
  fi

  emit_stdout "$(iso_now) [CLEANUP_FAIL] Could not fully clean simulated artifacts"
  echo "$(iso_now) syslog auth: CLEANUP_ERROR detected" >> "${SIM_SYSLOG_FILE}"
  return 1
}

pick_random_technique() {
  echo "${TECHNIQUES[$((RANDOM % ${#TECHNIQUES[@]}))]}"
}

next_sleep_seconds() {
  if [[ "${ATTACK_MODE}" == "fixed" ]]; then
    echo "${ATTACK_INTERVAL}"
    return
  fi

  local lo="${ATTACK_INTERVAL_MIN}"
  local hi="${ATTACK_INTERVAL_MAX}"
  if (( hi < lo )); then
    local t="${lo}"
    lo="${hi}"
    hi="${t}"
  fi
  echo $(( RANDOM % (hi - lo + 1) + lo ))
}

on_shutdown() {
  emit_stdout "$(iso_now) app {\"level\":\"INFO\",\"msg\":\"Signal received, graceful shutdown started\"}"

  if [[ -n "${flog_pid}" ]] && kill -0 "${flog_pid}" >/dev/null 2>&1; then
    kill "${flog_pid}" >/dev/null 2>&1 || true
  fi

  if [[ -n "${main_pid}" ]] && kill -0 "${main_pid}" >/dev/null 2>&1; then
    kill "${main_pid}" >/dev/null 2>&1 || true
  fi

  perform_cleanup || true
  rm -f "${ORCHESTRATOR_PID_FILE}"
  emit_stdout "$(iso_now) app {\"level\":\"INFO\",\"msg\":\"Graceful shutdown completed\"}"
  exit 0
}

main_loop() {
  while true; do
    if [[ -f "${STOP_REQUEST_FILE}" ]]; then
      break
    fi

    run_noise_batch

    local sleep_for
    sleep_for="$(next_sleep_seconds)"

    # Keep noise running while waiting for the next attack.
    local passed=0
    while (( passed < sleep_for )); do
      if [[ -f "${STOP_REQUEST_FILE}" ]]; then
        break 2
      fi
      sleep 1
      passed=$((passed + 1))
      run_noise_batch
    done

    if [[ -f "${STOP_REQUEST_FILE}" ]]; then
      break
    fi

    if [[ "${ATTACK_MODE}" == "fixed" ]]; then
      run_technique "${FIXED_TECHNIQUE}"
    else
      run_technique "$(pick_random_technique)"
    fi
  done
}

bootstrap() {
  RANDOM="${RANDOM_SEED}"
  mkdir -p /var/log/golden

  # Keep append-only stream across restarts to preserve external log continuity.
  touch "${STREAM_LOG_FILE}"
  : > "${SIM_SYSLOG_FILE}"
  epoch_now > "${LAST_STDOUT_TS_FILE}"
  rm -f "${UNHEALTHY_FLAG_FILE}"
  rm -f "${STOP_REQUEST_FILE}"

  echo "$$" > "${ORCHESTRATOR_PID_FILE}"
  validate_env

  emit_stdout "$(iso_now) app {\"level\":\"INFO\",\"msg\":\"Orchestrator started\",\"mode\":\"${ATTACK_MODE}\",\"log_rate\":${LOG_RATE},\"seed\":${RANDOM_SEED},\"host\":\"${HOSTNAME_OVERRIDE}\",\"stream_file\":\"${STREAM_LOG_FILE}\"}"
  start_flog_noise

  main_loop &
  main_pid="$!"
  wait "${main_pid}"

  on_shutdown
}

trap on_shutdown SIGTERM SIGINT
bootstrap
