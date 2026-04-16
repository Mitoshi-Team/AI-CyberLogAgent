local function read_env_int(name, default_value, min_value)
  if os == nil or os.getenv == nil then
    return default_value
  end

  local raw = os.getenv(name)
  if raw == nil or raw:match("^%s*$") then
    return default_value
  end

  local value = tonumber(raw)
  if value == nil then
    return default_value
  end

  value = math.floor(value)
  if min_value ~= nil and value < min_value then
    return default_value
  end

  return value
end

local BATCH_SIZE = read_env_int("CHUNK_BATCH_SIZE", 250, 1)
local OVERLAP = read_env_int("CHUNK_OVERLAP", 20, 0)
local FLUSH_INTERVAL_SECONDS = read_env_int("CHUNK_FLUSH_INTERVAL_SECONDS", 300, 1)

local state = {
  queue = {},
  first_ts = nil,
}

local function trim(value)
  return (value:gsub("^%s+", ""):gsub("%s+$", ""))
end

local function is_probable_log_line(message)
  -- Empty or whitespace-only lines are not logs.
  if message == nil then
    return false
  end

  local text = trim(message)
  if text == "" then
    return false
  end

  -- Heuristics: accept if line has common log structure tokens.
  local has_brackets = text:find("[%[%]%(%)%{%}]") ~= nil
  local has_level = text:find("%f[%a][Ee][Rr][Rr][Oo][Rr]%f[%A]") ~= nil
    or text:find("%f[%a][Ww][Aa][Rr][Nn]%f[%A]") ~= nil
    or text:find("%f[%a][Ii][Nn][Ff][Oo]%f[%A]") ~= nil
    or text:find("%f[%a][Dd][Ee][Bb][Uu][Gg]%f[%A]") ~= nil
    or text:find("%f[%a][Tt][Rr][Aa][Cc][Ee]%f[%A]") ~= nil
  local has_timestamp = text:find("%d%d%d%d%-%d%d%-%d%d") ~= nil
    or text:find("%d%d:%d%d:%d%d") ~= nil
  local has_kv = text:find("[%w_%-]+=") ~= nil

  return has_brackets or has_level or has_timestamp or has_kv
end

local function build_batch(queue)
  local records = {}
  local seen_sources = {}
  local source_files = {}

  for i = 1, #queue do
    records[i] = queue[i]

    local source = queue[i].file_path or "unknown"
    if not seen_sources[source] then
      seen_sources[source] = true
      source_files[#source_files + 1] = source
    end
  end

  local source_file = "mixed"
  if #source_files == 1 then
    source_file = source_files[1]
  end

  return {
    log = {
      source_file = source_file,
      source_files = source_files,
      records = records,
      batch_size = #records,
      overlap = OVERLAP,
      collected_at = os.date("!%Y-%m-%dT%H:%M:%SZ")
    }
  }
end

local function keep_tail(queue)
  local start_idx = math.max(1, #queue - OVERLAP + 1)
  local tail = {}
  for i = start_idx, #queue do
    tail[#tail + 1] = queue[i]
  end
  return tail
end

local function flush_if_due(emit, now_ts)
  local queue = state.queue

  if #queue == 0 or state.first_ts == nil then
    return
  end

  if now_ts - state.first_ts < FLUSH_INTERVAL_SECONDS then
    return
  end

  emit(build_batch(queue))
  state.queue = keep_tail(queue)
  state.first_ts = now_ts
end

function process(event, emit)
  local now_ts = os.time()

  -- Non-log events (heartbeat metrics) are used only to trigger timed flush checks.
  local log = event.log
  if log == nil then
    flush_if_due(emit, now_ts)
    return
  end

  local message = trim(log.message or "")
  if not is_probable_log_line(message) then
    flush_if_due(emit, now_ts)
    return
  end

  local file_path = log.file_path or "unknown"
  local queue = state.queue

  if state.first_ts == nil then
    state.first_ts = now_ts
  end

  queue[#queue + 1] = {
    message = message,
    timestamp = log.timestamp,
    file_path = file_path
  }

  if #queue >= BATCH_SIZE then
    emit(build_batch(queue))

    state.queue = keep_tail(queue)
    state.first_ts = now_ts
    return
  end

  flush_if_due(emit, now_ts)
end
