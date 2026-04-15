"""Sigma rules engine adapted for text-based log analysis.

Sigma rules are YAML-based detection rules originally designed for SIEM systems.
This engine adapts them for direct log text analysis by:
1. Parsing Sigma YAML rule files
2. Extracting detection patterns and conditions
3. Converting Sigma detection logic to text matching
4. Returning structured match results with severity and MITRE references
"""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Severity level mapping from Sigma to numeric
SEVERITY_MAP = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "informational": 0,
}


class SigmaRule:
    """Represents a single parsed Sigma rule."""

    def __init__(
        self,
        rule_id: str,
        title: str,
        description: str,
        status: str,
        author: str,
        level: str,
        tags: list[str],
        references: list[str],
        detection: dict,
        falsepositives: list[str],
    ):
        self.rule_id = rule_id
        self.title = title
        self.description = description
        self.status = status
        self.author = author
        self.level = level
        self.tags = tags
        self.references = references
        self.detection = detection
        self.falsepositives = falsepositives
        self._patterns: dict[str, list[str]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Extract all searchable patterns from the detection section."""
        detection = self.detection
        if not isinstance(detection, dict):
            return

        # The 'condition' field tells us how to combine selections
        # We extract all selection patterns
        condition = detection.get("condition", "")
        self._condition_str = condition if isinstance(condition, str) else ""

        # Extract all selection_* dicts
        for key, value in detection.items():
            if key == "condition" or not isinstance(value, dict):
                continue
            patterns = self._extract_patterns(value)
            if patterns:
                self._patterns[key] = patterns

    def _extract_patterns(self, detection_block: dict) -> list[str]:
        """Extract regex-escaped search patterns from a detection block.

        Sigma detection blocks look like:
            selection:
                CommandLine|contains:
                    - 'pattern1'
                    - 'pattern2'
                EventID: 4625

        We convert these to search patterns for log text matching.
        """
        patterns = []
        for field, value in detection_block.items():
            modifier = field.split("|")[1].lower() if "|" in field else ""

            values = value if isinstance(value, list) else [value]

            for v in values:
                v_str = str(v)
                if modifier == "contains":
                    # Simple substring match (case-insensitive)
                    patterns.append(v_str.lower())
                elif modifier in ("startswith", "endswith"):
                    patterns.append(v_str.lower())
                elif modifier == "all":
                    # Must match ALL sub-patterns (for 'all' operator)
                    patterns.append(v_str.lower())
                elif modifier == "re":
                    # Regex pattern
                    patterns.append(f"REGEX:{v_str}")
                else:
                    # Exact match
                    patterns.append(v_str.lower())

        return patterns

    def _check_selection(self, selection_key: str, text: str) -> bool:
        """Check if a specific selection block matches the text."""
        if selection_key not in self._patterns:
            return False

        text_lower = text.lower()
        patterns = self._patterns[selection_key]

        # Check the original detection block for 'all' modifier
        detection_block = self.detection.get(selection_key, {})
        for field, value in detection_block.items():
            modifier = field.split("|")[1].lower() if "|" in field else ""
            if modifier == "all" and isinstance(value, list):
                # ALL patterns must match
                return all(p.lower() in text_lower for p in value)

        # Default: ANY pattern in the selection must match
        return any(p in text_lower for p in patterns)

    def match(self, text: str) -> tuple[bool, list[str]]:
        """Evaluate the rule against log text.

        Returns:
            (matched, list_of_matched_selection_names)
        """
        if not self._patterns:
            return False, []

        condition = self._condition_str.lower()
        matched_selections = []

        # Check each selection block
        for key in self._patterns:
            if self._check_selection(key, text):
                matched_selections.append(key)

        if not matched_selections:
            return False, []

        # Evaluate the condition expression
        result = self._evaluate_condition(condition, matched_selections)
        return result, matched_selections

    def _evaluate_condition(self, condition: str, matched: list[str]) -> bool:
        """Parse and evaluate Sigma condition expression.

        Supports:
        - "selection" — single selection block
        - "selection1 or selection2"
        - "selection1 and selection2"
        - "selection_union or selection_tautology or ..."
        """
        if not condition:
            return len(matched) > 0

        condition = condition.strip().lower()

        # Single identifier
        if re.match(r"^\w+$", condition):
            return condition in matched

        # Boolean expression: "a or b", "a and b"
        try:
            # Build expression with True/False for each selection
            expr = condition
            for key in self._patterns:
                present = key in matched
                expr = re.sub(rf"\b{re.escape(key)}\b", str(present), expr)

            # Handle 'not' operator
            expr = expr.replace(" not ", " not ")

            return bool(eval(expr))  # noqa: S307 — controlled input
        except Exception as e:
            logger.warning(
                f"Failed to evaluate Sigma condition '{condition}' for rule '{self.title}': {e}"
            )
            return len(matched) > 0

    def get_mitre_techniques(self) -> list[str]:
        """Extract MITRE ATT&CK technique IDs from tags."""
        techniques = []
        for tag in self.tags:
            if tag.startswith("attack.t"):
                techniques.append(tag.split(".")[1].upper())
        return techniques


class SigmaEngine:
    """Engine that loads Sigma YAML rules and scans text content.

    Adapted for log analysis: instead of SIEM event correlation,
    it applies Sigma pattern matching against raw log text.
    """

    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self.rules: list[SigmaRule] = []
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

        logger.info(f"Loaded {len(self.rules)} Sigma rules from {self.rules_path}")

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
                self.rules.append(rule)
                logger.debug(f"Parsed rule '{rule.title}' from {filepath.name}")

        except yaml.YAMLError as e:
            logger.error(f"YAML parse error in {filepath}: {e}")
        except Exception as e:
            logger.error(f"Failed to parse Sigma file {filepath}: {e}")

    def _build_rule(self, data: dict) -> SigmaRule | None:
        """Build a SigmaRule from parsed YAML data."""
        try:
            rule_id = data.get("id", "")
            title = data.get("title", "Unknown")
            description = data.get("description", "")
            status = data.get("status", "experimental")
            author = data.get("author", "")
            level = data.get("level", "medium")
            tags = data.get("tags", [])
            references = data.get("references", [])
            detection = data.get("detection", {})
            falsepositives = data.get("falsepositives", [])

            if not detection:
                logger.warning(f"Sigma rule '{title}' has no detection section")
                return None

            return SigmaRule(
                rule_id=rule_id,
                title=title,
                description=description,
                status=status,
                author=author,
                level=level,
                tags=tags if isinstance(tags, list) else [],
                references=references if isinstance(references, list) else [],
                detection=detection,
                falsepositives=falsepositives
                if isinstance(falsepositives, list)
                else [],
            )

        except Exception as e:
            logger.error(f"Failed to build Sigma rule: {e}")
            return None

    def scan(self, log_content: str) -> list[dict[str, Any]]:
        """Scan log content against all loaded Sigma rules.

        Args:
            log_content: Raw log text to analyze

        Returns:
            List of match dictionaries with rule info and matched selections
        """
        results = []

        for rule in self.rules:
            matched, matched_selections = rule.match(log_content)
            if matched:
                results.append(
                    {
                        "rule_id": rule.rule_id,
                        "title": rule.title,
                        "description": rule.description,
                        "severity": rule.level,
                        "severity_numeric": SEVERITY_MAP.get(rule.level, 0),
                        "tags": rule.tags,
                        "mitre_techniques": rule.get_mitre_techniques(),
                        "references": rule.references,
                        "matched_selections": matched_selections,
                        "falsepositives": rule.falsepositives,
                    }
                )

        logger.info(
            f"Sigma scan complete: {len(results)} rules matched out of {len(self.rules)} loaded"
        )
        return results
