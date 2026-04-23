"""Sigma rules engine using pysigma for text-based log analysis."""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "informational": 0,
}


class SigmaEngine:
    """Engine that loads Sigma YAML rules and scans parsed log data.

    Uses field-based matching against structured log entries, supporting
    Sigma modifiers like contains, startswith, endswith, re.
    """

    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self._rules: list[dict] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Parse all .yml/.yaml files from the rules directory."""
        if not self.rules_path.exists():
            logger.warning(f"Sigma rules path does not exist: {self.rules_path}")
            return

        yml_files = list(self.rules_path.glob("*.yml")) + list(
            self.rules_path.glob("*.yaml")
        )
        if not yml_files:
            logger.warning(f"No .yml files found in {self.rules_path}")
            return

        for yml_file in yml_files:
            self._parse_sigma_file(yml_file)

        logger.info(f"Loaded {len(self._rules)} Sigma rules from {self.rules_path}")

    def _parse_sigma_file(self, filepath: Path) -> None:
        """Parse a single Sigma YAML file."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data or not isinstance(data, dict):
                logger.warning(f"Invalid Sigma rule in {filepath}")
                return

            rule = self._build_rule(data)
            if rule:
                self._rules.append(rule)
                logger.debug(f"Parsed rule '{rule['title']}' from {filepath.name}")

        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {filepath}: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Sigma file {filepath}: {e}")

    def _build_rule(self, data: dict) -> dict | None:
        """Build a rule dict from parsed YAML data."""
        try:
            detection = data.get("detection", {})
            if not detection:
                logger.warning(
                    f"Sigma rule '{data.get('title')}' has no detection section"
                )
                return None

            selections = {}
            for key, value in detection.items():
                if key == "condition" or not isinstance(value, dict):
                    continue
                selections[key] = self._parse_selection(value)

            return {
                "rule_id": data.get("id", ""),
                "title": data.get("title", "Unknown"),
                "description": data.get("description", ""),
                "level": data.get("level", "medium"),
                "tags": data.get("tags", []),
                "references": data.get("references", []),
                "falsepositives": data.get("falsepositives", []),
                "condition": detection.get("condition", ""),
                "selections": selections,
            }

        except Exception as e:
            logger.error(f"Failed to build Sigma rule: {e}")
            return None

    def _parse_selection(self, selection: dict) -> list[tuple[str, str, str]]:
        """Parse a Sigma selection block.

        Returns:
            List of (field, modifier, value) tuples.

        """
        parsed = []

        for field, value in selection.items():
            if "|" in field:
                field_name, modifier = field.split("|", 1)
            else:
                field_name = field
                modifier = "equals"

            values = value if isinstance(value, list) else [value]

            for v in values:
                parsed.append((field_name.lower(), modifier.lower(), str(v)))

        return parsed

    def scan(self, parsed_logs: list[dict]) -> list[dict[str, Any]]:
        """Scan parsed logs against all loaded Sigma rules.

        Args:
            parsed_logs: List of parsed log dictionaries from ApacheLogParser.

        Returns:
            List of match dictionaries with rule info and matched fields.

        """
        results = []

        for rule in self._rules:
            matched_logs = self._match_rule(rule, parsed_logs)
            if matched_logs:
                results.append(
                    {
                        "rule_id": rule["rule_id"],
                        "title": rule["title"],
                        "description": rule["description"],
                        "severity": rule["level"],
                        "severity_numeric": SEVERITY_MAP.get(rule["level"], 0),
                        "tags": rule["tags"],
                        "mitre_techniques": self._get_mitre_techniques(rule["tags"]),
                        "references": rule["references"],
                        "falsepositives": rule["falsepositives"],
                        "matched_logs": matched_logs,
                    }
                )

        logger.info(
            f"Sigma scan complete: {len(results)} rules matched from {len(parsed_logs)} logs"
        )
        return results

    def scan_raw(self, text: str) -> list[dict[str, Any]]:
        """Scan raw text against all loaded Sigma rules (fallback).

        Args:
            text: Raw text to scan.

        Returns:
            List of match dictionaries.

        """
        results = []

        for rule in self._rules:
            matched_selections = self._match_text(rule, text)
            if matched_selections:
                results.append(
                    {
                        "rule_id": rule["rule_id"],
                        "title": rule["title"],
                        "description": rule["description"],
                        "severity": rule["level"],
                        "severity_numeric": SEVERITY_MAP.get(rule["level"], 0),
                        "tags": rule["tags"],
                        "mitre_techniques": self._get_mitre_techniques(rule["tags"]),
                        "references": rule["references"],
                        "matched_selections": matched_selections,
                        "falsepositives": rule["falsepositives"],
                    }
                )

        return results

    def _match_rule(self, rule: dict, parsed_logs: list[dict]) -> list[dict]:
        """Match a rule against parsed log entries."""
        matched_logs = []

        for i, log in enumerate(parsed_logs):
            log_text = self._log_to_text(log)
            matched_selections = self._match_text(rule, log_text)

            if matched_selections:
                matched_logs.append(
                    {
                        "log_index": i,
                        "matched_selections": matched_selections,
                        "log_preview": log_text[:200],
                    }
                )

        if not matched_logs:
            return []

        if self._evaluate_condition(rule["condition"], len(matched_logs)):
            return matched_logs

        return []

    def _match_text(self, rule: dict, text: str) -> list[str]:
        """Check which selections in a rule match the text."""
        matched = []
        text_lower = text.lower()

        for sel_name, conditions in rule["selections"].items():
            if self._selection_matches(conditions, text, text_lower):
                matched.append(sel_name)

        return matched

    def _selection_matches(self, conditions: list, text: str, text_lower: str) -> bool:
        """Check if all conditions in a selection match the text."""
        for field, modifier, value in conditions:
            if not self._check_condition(field, modifier, value, text, text_lower):
                return False
        return len(conditions) > 0

    def _check_condition(
        self, field: str, modifier: str, value: str, text: str, text_lower: str
    ) -> bool:
        """Check a single field condition against text."""
        value_lower = value.lower()

        if field in ("message", "uri", "query", "user_agent", "referer", "raw"):
            field_value = str(text.get(field, "") if isinstance(text, dict) else text)
        else:
            field_value = str(text) if isinstance(text, str) else ""

        field_lower = field_value.lower()

        if modifier == "contains":
            return value_lower in field_lower
        elif modifier == "startswith":
            return field_lower.startswith(value_lower)
        elif modifier == "endswith":
            return field_lower.endswith(value_lower)
        elif modifier == "equals":
            return field_lower == value_lower
        elif modifier == "re":
            try:
                return bool(re.search(value, field_value, re.IGNORECASE))
            except re.error:
                return False
        else:
            return value_lower in field_lower

    def _evaluate_condition(self, condition: str, match_count: int) -> bool:
        """Evaluate a Sigma condition expression."""
        if not condition:
            return match_count > 0

        condition = condition.strip().lower()

        n_of_match = re.match(r"(\d+)\s+of\s+selection", condition)
        if n_of_match:
            required = int(n_of_match.group(1))
            return match_count >= required

        if "of selection" in condition:
            return match_count > 0

        return match_count > 0

    def _log_to_text(self, log: dict) -> str:
        """Convert a parsed log dict to text for matching."""
        parts = [
            log.get("message", ""),
            log.get("uri", ""),
            log.get("query", ""),
            log.get("user_agent", ""),
            log.get("referer", ""),
            log.get("client_ip", ""),
            log.get("method", ""),
            log.get("raw", ""),
        ]
        return " ".join(filter(None, parts))

    @staticmethod
    def _get_mitre_techniques(tags: list[str]) -> list[str]:
        """Extract MITRE ATT&CK technique IDs from tags."""
        techniques = []
        for tag in tags:
            if tag.startswith("attack.t"):
                techniques.append(tag.split(".")[1].upper())
        return techniques
