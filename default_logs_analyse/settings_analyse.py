"""
Settings for the log analysis module.
"""

# Path to collect logs from
SOURCE_LOG_PATH = "../other_project/logs/"

# Path to store processed logs
PROCESSED_LOG_PATH = "collected_logs"

# Path to store incidents
INCIDENTS_OUTPUT_PATH = "incidents"

# Log file extensions to collect
LOG_FILE_PATTERN = "*.log"

# Keywords that indicate an incident
INCIDENT_KEYWORDS = [
    "ERROR",
    "CRITICAL",
    "EXCEPTION",
    "FATAL",
    "WARNING"
]

# File encoding
LOG_FILE_ENCODING = "utf-8"

# Batch size for processing logs
BATCH_SIZE = 100
