"""Module for analyzing collected logs using AI to understand the context
and detect incidents based on semantic meaning rather than just patterns.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from settings_analyse import (
    INCIDENTS_OUTPUT_PATH,
    LOG_FILE_ENCODING,
    PROCESSED_LOG_PATH,
)

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/analyzer.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class LogAnalyzer:
    """Advanced log analyzer using lightweight heuristics and contextual analysis
    to detect incidents based on semantic meaning without heavy AI models.
    """

    def __init__(self):
        """Initialize the log analyzer with contextual analysis rules."""
        self.incident_patterns = [
            # Error patterns
            r"error",
            r"exception",
            r"critical",
            r"fatal",
            r"fail",
            r"timeout",
            r"connection refused",
            r"permission denied",
            r"out of memory",
            r"deadlock",
            r"corruption",
            # Security patterns
            r"unauthorized",
            r"authentication failed",
            r"security violation",
            r"brute force",
            r"sql injection",
            r"xss",
            r"csrf",
            # System stability patterns
            r"high cpu",
            r"high memory",
            r"disk full",
            r"service down",
            r"heartbeat failed",
            r"watchdog triggered",
        ]

        # Contextual indicators that increase incident severity
        self.context_indicators = {
            "repeated": [r"failed (\d+) times", r"retry (\d+)", r"attempt (\d+)"],
            "system_wide": [r"all services", r"cluster", r"global", r"entire system"],
            "user_impact": [
                r"users affected",
                r"customers impacted",
                r"service disruption",
            ],
            "data_loss": [r"data loss", r"corrupted", r"irreversible"],
        }

    def _normalize_text(self, text: str) -> str:
        """Normalize text for pattern matching."""
        return text.strip().lower()

    def _matches_pattern(self, text: str, patterns: list) -> bool:
        """Check if text matches any pattern."""
        text_lower = self._normalize_text(text)
        return any(pattern in text_lower for pattern in patterns)

    def _calculate_context_score(
        self, lines: list[str], line_idx: int
    ) -> dict[str, Any]:
        """Calculate context score based on surrounding lines and patterns."""
        score = 0.0
        details = {
            "repeated": False,
            "system_wide": False,
            "user_impact": False,
            "data_loss": False,
            "nearby_errors": 0,
        }

        # Check context within 5 lines before and after
        start = max(0, line_idx - 5)
        end = min(len(lines), line_idx + 6)

        for i in range(start, end):
            line = lines[i]
            if i != line_idx:  # Don't count the line itself
                if self._matches_pattern(line, [r"error", r"exception", r"fail"]):
                    details["nearby_errors"] += 1

            # Check for contextual indicators
            for context_type, patterns in self.context_indicators.items():
                if self._matches_pattern(line, patterns):
                    details[context_type] = True
                    if context_type == "repeated":
                        score += 0.3
                    elif context_type == "system_wide":
                        score += 0.4
                    elif context_type == "user_impact":
                        score += 0.3
                    elif context_type == "data_loss":
                        score += 0.5

        # Boost score based on nearby errors
        score += min(details["nearby_errors"] * 0.1, 0.3)

        return {"score": score, "details": details}

    def _extract_context(
        self, lines: list[str], line_idx: int, context_size: int = 5
    ) -> str:
        """Extract context around a log line.

        Args:
            lines (List[str]): All lines in the log file
            line_idx (int): Index of the target line
            context_size (int): Number of lines before and after to include

        Returns:
            str: Contextual log lines

        """
        start = max(0, line_idx - context_size)
        end = min(len(lines), line_idx + context_size + 1)

        context_lines = []
        for i in range(start, end):
            prefix = "--> " if i == line_idx else "    "
            context_lines.append(f"{prefix}{lines[i].strip()}")

        return "\n".join(context_lines)

    def _assess_incident_severity(
        self, base_confidence: float, context_score: float
    ) -> str:
        """Assess incident severity based on confidence and context."""
        total_score = base_confidence + context_score

        if total_score >= 0.8:
            return "CRITICAL"
        elif total_score >= 0.6:
            return "HIGH"
        elif total_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"

    def analyze_log_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Analyze a single log file and extract incidents.

        Args:
            file_path (Path): Path to the log file

        Returns:
            List of incident dictionaries

        """
        logger.info(f"Analyzing log file: {file_path}")

        try:
            with open(file_path, encoding=LOG_FILE_ENCODING) as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

        incidents = []
        total_lines = len(lines)

        logger.info(f"Processing {total_lines} lines from {file_path.name}")

        for line_num, line in enumerate(lines, 1):
            if not line:
                continue

            # Check if line matches any incident pattern
            if self._matches_pattern(line, self.incident_patterns):
                # Calculate context score
                context_analysis = self._calculate_context_score(lines, line_num - 1)

                # Base confidence from pattern match
                base_confidence = 0.7

                # Calculate total confidence
                total_confidence = min(base_confidence + context_analysis["score"], 1.0)

                # Extract context
                context = self._extract_context(lines, line_num - 1)

                # Assess severity
                severity = self._assess_incident_severity(
                    base_confidence, context_analysis["score"]
                )

                incident = {
                    "line_number": line_num,
                    "content": line,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": round(total_confidence, 3),
                    "severity": severity,
                    "detection_method": "contextual_analysis",
                    "context": context,
                    "context_details": context_analysis["details"],
                }

                incidents.append(incident)
                logger.info(
                    f"Incident detected at line {line_num} with confidence {total_confidence:.2f} and severity {severity}"
                )

        logger.info(f"Found {len(incidents)} incidents in {file_path.name}")
        return incidents

    def analyze_logs(self) -> dict[str, Any]:
        """Analyze all collected log files and extract incidents.

        Returns:
            Dictionary with analysis results

        """
        processed_path = Path(PROCESSED_LOG_PATH)

        if not processed_path.exists():
            logger.error(f"Processed log path does not exist: {processed_path}")
            return {
                "success": False,
                "error": f"Processed log path does not exist: {processed_path}",
            }

        log_files = list(processed_path.glob("*.log"))

        if not log_files:
            logger.info("No log files found to analyze")
            return {
                "success": True,
                "total_files": 0,
                "total_incidents": 0,
                "incidents_by_file": {},
            }

        results = {
            "success": True,
            "total_files": len(log_files),
            "total_incidents": 0,
            "incidents_by_file": {},
        }

        for log_file in log_files:
            logger.info(f"\nAnalyzing {log_file.name}...")
            print(f"Analyzing {log_file.name}...")

            incidents = self.analyze_log_file(log_file)
            results["incidents_by_file"][log_file.name] = incidents
            results["total_incidents"] += len(incidents)

            if incidents:
                self._save_incidents(incidents, log_file.name)
                print(f"Found {len(incidents)} incident(s)")
            else:
                print("No incidents found")

        logger.info(
            f"Analysis completed. Total incidents found: {results['total_incidents']}"
        )

        # Save overall results
        self._save_overall_results(results)

        return results

    def _save_incidents(self, incidents: list[dict[str, Any]], source_file_name: str):
        """Saves detected incidents to a JSON file.

        Args:
            incidents (list): List of incident dictionaries.
            source_file_name (str): Name of the source log file.

        """
        incidents_path = Path(INCIDENTS_OUTPUT_PATH)
        incidents_path.mkdir(parents=True, exist_ok=True)

        output_file = incidents_path / f"incidents_{source_file_name}.json"

        data = {
            "source_file": source_file_name,
            "analysis_time": datetime.now().isoformat(),
            "analyzer_version": "2.0",
            "detection_method": "contextual_semantic_analysis",
            "total_incidents": len(incidents),
            "incidents": incidents,
        }

        try:
            with open(output_file, "w", encoding=LOG_FILE_ENCODING) as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Incidents saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save incidents: {e}")

    def _save_overall_results(self, results: dict[str, Any]):
        """Save overall analysis results.

        Args:
            results (Dict): Analysis results dictionary

        """
        incidents_path = Path(INCIDENTS_OUTPUT_PATH)
        incidents_path.mkdir(parents=True, exist_ok=True)

        output_file = incidents_path / "analysis_summary.json"

        try:
            with open(output_file, "w", encoding=LOG_FILE_ENCODING) as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Overall results saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save overall results: {e}")


def analyze_logs():
    """Analyzes all collected log files and extracts incidents using contextual analysis."""
    analyzer = LogAnalyzer()
    results = analyzer.analyze_logs()

    if results["success"]:
        print(
            f"\nAnalysis completed. Total incidents found: {results['total_incidents']}"
        )
    else:
        print(f"\nAnalysis failed: {results['error']}")

    return results


def main():
    """Main function to run the contextual log analyzer."""
    print("Starting contextual log analysis...")
    analyze_logs()
    print("Log analysis completed.")


if __name__ == "__main__":
    main()
