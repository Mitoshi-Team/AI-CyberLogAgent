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

local function read_env_string(name, default_value)
  if os == nil or os.getenv == nil then
    return default_value
  end

  local raw = os.getenv(name)
  if raw == nil or raw:match("^%s*$") then
    return default_value
  end

  return raw
end

local BATCH_SIZE = read_env_int("CHUNK_BATCH_SIZE", 250, 1)
local OVERLAP = read_env_int("CHUNK_OVERLAP", 20, 0)
local FLUSH_INTERVAL_SECONDS = read_env_int("CHUNK_FLUSH_INTERVAL_SECONDS", 180, 1)
local STATE_FILE = read_env_string("CHUNK_STATE_FILE", "/var/lib/vector/chunk_logs_state.tsv")
local RESET_MARKER_FILE = read_env_string("CHUNK_RESET_MARKER_FILE", "/data/external/.chunk_state_reset")

local state = {
  queue = {},
  first_ts = nil,
  next_record_seq = 1,
  next_batch_seq = 1,
  last_emitted_record_seq = 0,
}

local function split_tab(line)
  local fields = {}
  for token in string.gmatch(line, "([^\t]+)") do
    fields[#fields + 1] = token
  end
  return fields
end

local function escape_field(value)
  local text = tostring(value or "")
  text = text:gsub("\\", "\\\\")
  text = text:gsub("\t", "\\t")
  text = text:gsub("\n", "\\n")
  text = text:gsub("\r", "\\r")
  return text
end

local function unescape_field(value)
  if value == nil then
    return ""
  end

  local out = {}
  local i = 1
  while i <= #value do
    local c = value:sub(i, i)
    if c == "\\" and i < #value then
      local n = value:sub(i + 1, i + 1)
      if n == "t" then
        out[#out + 1] = "\t"
      elseif n == "n" then
        out[#out + 1] = "\n"
      elseif n == "r" then
        out[#out + 1] = "\r"
      else
        out[#out + 1] = n
      end
      i = i + 2
    else
      out[#out + 1] = c
      i = i + 1
    end
  end

  return table.concat(out)
end

local function persist_state()
  local tmp_path = STATE_FILE .. ".tmp"
  local file_obj = io.open(tmp_path, "w")
  if file_obj == nil then
    return
  end

  local first_ts = state.first_ts or -1
  file_obj:write(
    string.format(
      "H\t%d\t%d\t%d\t%d\n",
      first_ts,
      state.next_record_seq,
      state.next_batch_seq,
      state.last_emitted_record_seq
    )
  )

  for i = 1, #state.queue do
    local record = state.queue[i]
    file_obj:write(
      string.format(
        "Q\t%d\t%s\t%s\t%s\n",
        record.stream_seq or 0,
        escape_field(record.file_path or "unknown"),
        escape_field(record.timestamp or ""),
        escape_field(record.message or "")
      )
    )
  end

  file_obj:close()
  os.rename(tmp_path, STATE_FILE)
end

local function restore_state()
  local file_obj = io.open(STATE_FILE, "r")
  if file_obj == nil then
    return
  end

  local restored_queue = {}

  for raw_line in file_obj:lines() do
    local line = raw_line:gsub("\r$", "")
    local fields = split_tab(line)
    local kind = fields[1]

    if kind == "H" then
      local first_ts = tonumber(fields[2])
      local next_record_seq = tonumber(fields[3])
      local next_batch_seq = tonumber(fields[4])
      local last_emitted_record_seq = tonumber(fields[5])

      if first_ts ~= nil and first_ts >= 0 then
        state.first_ts = first_ts
      else
        state.first_ts = nil
      end

      if next_record_seq ~= nil and next_record_seq > 0 then
        state.next_record_seq = next_record_seq
      end

      if next_batch_seq ~= nil and next_batch_seq > 0 then
        state.next_batch_seq = next_batch_seq
      end

      if last_emitted_record_seq ~= nil and last_emitted_record_seq >= 0 then
        state.last_emitted_record_seq = last_emitted_record_seq
      end
    elseif kind == "Q" then
      local stream_seq = tonumber(fields[2]) or 0
      restored_queue[#restored_queue + 1] = {
        stream_seq = stream_seq,
        file_path = unescape_field(fields[3]),
        timestamp = unescape_field(fields[4]),
        message = unescape_field(fields[5]),
      }
    end
  end

  file_obj:close()

  state.queue = restored_queue
  if #state.queue == 0 then
    state.first_ts = nil
  end

  local max_seq = state.last_emitted_record_seq
  for i = 1, #state.queue do
    local seq = state.queue[i].stream_seq or 0
    if seq > max_seq then
      max_seq = seq
    end
  end

  if state.next_record_seq <= max_seq then
    state.next_record_seq = max_seq + 1
  end
end

restore_state()

local function reset_runtime_state()
  state.queue = {}
  state.first_ts = nil
  state.next_record_seq = 1
  state.next_batch_seq = 1
  state.last_emitted_record_seq = 0
  persist_state()
end

local function consume_reset_marker_if_present()
  local marker_file = io.open(RESET_MARKER_FILE, "r")
  if marker_file == nil then
    return
  end

  marker_file:close()
  os.remove(RESET_MARKER_FILE)
  reset_runtime_state()
end

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

local function build_batch(queue_records)
  local records = {}
  local seen_sources = {}
  local source_files = {}

  for i = 1, #queue_records do
    records[i] = queue_records[i]

    local source = records[i].file_path or "unknown"
    if not seen_sources[source] then
      seen_sources[source] = true
      source_files[#source_files + 1] = source
    end
  end

  local source_file = "mixed"
  if #source_files == 1 then
    source_file = source_files[1]
  end

  local batch_seq = state.next_batch_seq
  state.next_batch_seq = batch_seq + 1

  local first_seq = records[1] and records[1].stream_seq or state.last_emitted_record_seq
  local last_seq = records[#records] and records[#records].stream_seq or state.last_emitted_record_seq

  local collected_at_compact = os.date("!%Y%m%dT%H%M%SZ")

  return {
    log = {
      source_file = source_file,
      source_files = source_files,
      records = records,
      batch_size = #records,
      overlap = OVERLAP,
      collected_at = os.date("!%Y-%m-%dT%H:%M:%SZ"),
      collected_at_compact = collected_at_compact,
      batch_sequence = batch_seq,
      start_record_sequence = first_seq,
      end_record_sequence = last_seq
    }
  }
end

local function keep_tail(records)
  local start_idx = math.max(1, #records - OVERLAP + 1)
  local tail = {}
  for i = start_idx, #records do
    tail[#tail + 1] = records[i]
  end
  return tail
end

local function append_records(target, source)
  for i = 1, #source do
    target[#target + 1] = source[i]
  end
end

local function has_unemitted_records(queue)
  local last_record = queue[#queue]
  if last_record == nil then
    return false
  end

  local last_seq = last_record.stream_seq or 0
  return last_seq > state.last_emitted_record_seq
end

local function emit_records(records, emit)
  local last_record = records[#records]
  if last_record == nil then
    return false
  end

  local last_seq = last_record.stream_seq or 0
  if last_seq <= state.last_emitted_record_seq then
    return false
  end

  emit(build_batch(records))
  state.last_emitted_record_seq = last_seq
  persist_state()
  return true
end

local function split_first_batch(queue)
  local batch = {}
  local remaining = {}

  for i = 1, #queue do
    if i <= BATCH_SIZE then
      batch[#batch + 1] = queue[i]
    else
      remaining[#remaining + 1] = queue[i]
    end
  end

  return batch, remaining
end

local function flush_full_batches(emit, now_ts)
  local queue = state.queue

  while #queue >= BATCH_SIZE do
    local batch, remaining = split_first_batch(queue)

    if not emit_records(batch, emit) then
      break
    end

    local tail = keep_tail(batch)
    local next_queue = {}
    append_records(next_queue, tail)
    append_records(next_queue, remaining)
    queue = next_queue
  end

  state.queue = queue
  if has_unemitted_records(queue) then
    state.first_ts = now_ts
  else
    state.first_ts = nil
  end

  persist_state()
end

local function flush_if_due(emit, now_ts)
  local queue = state.queue

  if #queue == 0 or state.first_ts == nil then
    return
  end

  if now_ts - state.first_ts < FLUSH_INTERVAL_SECONDS then
    return
  end

  if emit_records(queue, emit) then
    state.queue = keep_tail(queue)
  end

  if has_unemitted_records(state.queue) then
    state.first_ts = now_ts
  else
    state.first_ts = nil
  end
  persist_state()
end

function process(event, emit)
  consume_reset_marker_if_present()

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

  local current_record_seq = state.next_record_seq
  state.next_record_seq = current_record_seq + 1

  queue[#queue + 1] = {
    message = message,
    timestamp = log.timestamp,
    file_path = file_path,
    stream_seq = current_record_seq
  }

  persist_state()

  flush_full_batches(emit, now_ts)

  flush_if_due(emit, now_ts)
end
