class LogManageSettings:
    """Settings for log management.

    Attributes:
        logs_path (str): Path to the analyse_logs directory.
        logs_file (str): Name of the log file.
        logs_file_path (str): Full path to the log file.
        logs_file_size (int): Maximum size of the log file in bytes.

    """

    def __init__(self):
        """Initialize LogManageSettings with default values."""
        self.logs_path = "analyse_logs"
        self.logs_file = "analyse_logs.txt"
        self.logs_file_path = f"{self.logs_path}/{self.logs_file}"
        self.logs_file_size = 10000000  # 10 MB
