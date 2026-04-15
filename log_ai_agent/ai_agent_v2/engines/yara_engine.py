"""YARA rules engine adapted for text-based log analysis.

Since traditional YARA is designed for binary file scanning, this engine
adapts YARA rule syntax for log content analysis by:
1. Parsing YARA .yar files (rule structure, strings, conditions)
2. Converting YARA string patterns to Python regex
3. Matching against log text content
4. Returning structured match results
"""

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class YaraRule:
    """Represents a single parsed YARA rule."""

    def __init__(
        self,
        name: str,
        meta: dict[str, str],
        strings: dict[str, str],
        condition: str,
    ):
        self.name = name
        self.meta = meta
        self.strings = strings
        self.condition = condition
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile all string patterns into Python regex."""
        for key, pattern in self.strings.items():
            try:
                # YARA patterns use /regex/ syntax, strip delimiters
                clean = pattern.strip("/")
                # YARA uses \s* for spacing — ensure it works
                # Handle escaped forward slashes within the pattern
                clean = clean.replace(r"\/", "/")
                self._compiled_patterns[key] = re.compile(clean, re.IGNORECASE)
                logger.debug(f"Compiled pattern for rule '{self.name}', string '{key}'")
            except re.error as e:
                logger.warning(
                    f"Invalid regex in rule '{self.name}', string '{key}': {pattern} — {e}"
                )

    def match(self, text: str) -> tuple[bool, list[str]]:
        """Check if the rule matches the text.

        Returns:
            (matched, list_of_matched_string_keys)
        """
        matched_keys = []
        for key, pattern in self._compiled_patterns.items():
            if pattern.search(text):
                matched_keys.append(key)

        return len(matched_keys) > 0, matched_keys

    def evaluate_condition(self, matched_keys: list[str]) -> bool:
        """Evaluate the YARA condition based on matched strings.

        Supports common YARA condition syntax:
        - "1 of them"
        - "2 of them"
        - "all of them"
        - "any of them"
        - "$x1 and $x2"
        - "$x1 or $x2"
        """
        if not matched_keys:
            return False

        condition = self.condition.strip().lower()

        # "N of them" — at least N strings matched
        n_of_match = re.match(r"(\d+)\s+of\s+them", condition)
        if n_of_match:
            required = int(n_of_match.group(1))
            return len(matched_keys) >= required

        # "all of them"
        if condition == "all of them":
            return len(matched_keys) == len(self.strings)

        # "any of them"
        if condition == "any of them":
            return len(matched_keys) > 0

        # Boolean expression: "$a and $b", "$a or $b"
        # Replace $key with True/False
        expr = condition
        for key in self.strings:
            present = key in matched_keys
            expr = expr.replace(f"${key}", str(present))

        # Also handle "of ($*)" patterns like "1 of ($x*)"
        range_match = re.match(r"(\d+)\s+of\s+\(\$([^*]+)\*\)", expr)
        if range_match:
            required = int(range_match.group(1))
            prefix = f"${range_match.group(2)}"
            count = sum(1 for k in matched_keys if k.startswith(prefix))
            return count >= required

        try:
            return bool(eval(expr))  # noqa: S307 — controlled input from rules
        except Exception:
            logger.warning(
                f"Could not evaluate condition '{condition}' for rule '{self.name}'"
            )
            return len(matched_keys) > 0


class YaraEngine:
    """Engine that loads YARA rules and scans text content.

    Adapted for log analysis: instead of binary scanning,
    it applies YARA regex patterns against log text.
    """

    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self.rules: list[YaraRule] = []
        self._load_rules()

    def _load_rules(self) -> None:
        """Parse all .yar files from the rules directory."""
        if not self.rules_path.exists():
            logger.warning(f"YARA rules path does not exist: {self.rules_path}")
            return

        yar_files = list(self.rules_path.glob("*.yar"))
        if not yar_files:
            logger.warning(f"No .yar files found in {self.rules_path}")
            return

        for yar_file in yar_files:
            self._parse_yar_file(yar_file)

        logger.info(f"Loaded {len(self.rules)} YARA rules from {self.rules_path}")

    def _parse_yar_file(self, filepath: Path) -> None:
        """Parse a single .yar file and extract rules."""
        try:
            content = filepath.read_text(encoding="utf-8")
            rules = self._parse_yar_content(content)
            self.rules.extend(rules)
            logger.debug(f"Parsed {len(rules)} rules from {filepath.name}")
        except Exception as e:
            logger.error(f"Failed to parse YARA file {filepath}: {e}")

    def _parse_yar_content(self, content: str) -> list[YaraRule]:
        """Extract individual rules from YARA file content.

        Uses regex-based parsing to extract:
        - Rule name
        - Meta section (key-value pairs)
        - Strings section (pattern definitions)
        - Condition section
        """
        rules = []

        # Split into individual rule blocks
        # Pattern: rule <Name> { ... }
        rule_pattern = re.compile(
            r"rule\s+(\w+)\s*\{(.+?)\n\}",
            re.DOTALL,
        )

        for match in rule_pattern.finditer(content):
            rule_name = match.group(1)
            rule_body = match.group(2)

            try:
                meta = self._parse_meta_section(rule_body)
                strings = self._parse_strings_section(rule_body)
                condition = self._parse_condition(rule_body)

                if strings and condition:
                    rule = YaraRule(
                        name=rule_name,
                        meta=meta,
                        strings=strings,
                        condition=condition,
                    )
                    rules.append(rule)
                else:
                    logger.warning(
                        f"Rule '{rule_name}' skipped: missing strings or condition"
                    )

            except Exception as e:
                logger.error(f"Failed to parse rule '{rule_name}': {e}")

        return rules

    @staticmethod
    def _parse_meta_section(body: str) -> dict[str, str]:
        """Extract meta key-value pairs."""
        meta: dict[str, str] = {}
        meta_match = re.search(r"meta:\s*(.*?)strings:", body, re.DOTALL)
        if meta_match:
            meta_text = meta_match.group(1)
            for line in meta_text.strip().split("\n"):
                line = line.strip()
                kv = line.split("=", 1)
                if len(kv) == 2:
                    key = kv[0].strip()
                    value = kv[1].strip().strip('"')
                    meta[key] = value
        return meta

    @staticmethod
    def _parse_strings_section(body: str) -> dict[str, str]:
        """Extract string definitions from the strings section."""
        strings: dict[str, str] = {}
        strings_match = re.search(r"strings:\s*(.*?)condition:", body, re.DOTALL)
        if strings_match:
            strings_text = strings_match.group(1)
            # Match patterns like: $name = /regex/ or $name = "literal"
            for line in strings_text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Regex pattern: $key = /pattern/modifiers
                # Match from first / to last / before optional modifiers
                regex_match = re.match(r'(\$?\w+)\s*=\s*/(.+/)([a-z]*)$', line)
                if regex_match:
                    key = regex_match.group(1)
                    pattern = regex_match.group(2)
                    # Handle YARA modifiers (i, s, etc.)
                    modifiers = regex_match.group(3)
                    if "i" in modifiers:
                        pattern = f"(?i){pattern}"
                    strings[key] = pattern
                    continue

                # Literal string: $key = "text"
                literal_match = re.match(r'(\$?\w+)\s*=\s*"(.+?)"', line)
                if literal_match:
                    key = literal_match.group(1)
                    literal = re.escape(literal_match.group(2))
                    strings[key] = literal

        return strings

    @staticmethod
    def _parse_condition(body: str) -> str:
        """Extract the condition string."""
        cond_match = re.search(r"condition:\s*(.+)$", body, re.MULTILINE)
        if cond_match:
            return cond_match.group(1).strip()
        return ""

    def scan(self, log_content: str) -> list[dict[str, Any]]:
        """Scan log content against all loaded YARA rules.

        Args:
            log_content: Raw log text to analyze

        Returns:
            List of match dictionaries with rule info and matched strings
        """
        results = []

        for rule in self.rules:
            matched, matched_keys = rule.match(log_content)
            if matched and rule.evaluate_condition(matched_keys):
                results.append(
                    {
                        "rule": rule.name,
                        "description": rule.meta.get("description", ""),
                        "severity": rule.meta.get("severity", "unknown"),
                        "category": rule.meta.get("category", ""),
                        "mitre_ref": rule.meta.get("mitre_ref", ""),
                        "matched_strings": matched_keys,
                        "meta": rule.meta,
                    }
                )

        logger.info(
            f"YARA scan complete: {len(results)} rules matched out of {len(self.rules)} loaded"
        )
        return results
