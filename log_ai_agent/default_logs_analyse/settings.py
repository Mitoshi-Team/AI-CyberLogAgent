"""Settings for the log analysis module."""

# Path to collect analyse_logs from
SOURCE_LOG_PATH = "."

# Path to store processed analyse_logs
PROCESSED_LOG_PATH = "collected_logs"

# Path to store incidents
INCIDENTS_OUTPUT_PATH = "incidents"

# Log file extensions to collect
LOG_FILE_PATTERN = "*.log"

# Keywords that indicate an incident
INCIDENT_KEYWORDS = ["ERROR", "CRITICAL", "EXCEPTION", "FATAL", "WARNING"]

# File encoding
LOG_FILE_ENCODING = "utf-8"

# Batch size for processing analyse_logs
BATCH_SIZE = 100

# Paths to ignore during log collection
IGNORED_PATHS = ["app_simulation/log_gen/examples", "log_ai-agent"]
