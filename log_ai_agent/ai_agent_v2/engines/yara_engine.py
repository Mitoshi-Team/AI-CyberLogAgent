"""YARA rules engine using yara-python for text-based log analysis."""

import logging
from pathlib import Path
from typing import Any

import yara

logger = logging.getLogger(__name__)


class YaraEngine:
    """Engine that loads YARA rules and scans text content using yara-python.

    Uses yara.compile() and rules.match(data=...) for efficient pattern matching
    on structured log data.
    """

    def __init__(self, rules_path: str | Path):
        # rules_path can be a filesystem path or None. If rules_list is provided,
        # rules will be loaded from that list instead of the filesystem.
        # Track number of source rule documents for diagnostics
        self._source_count = 0
        self._rules_list: list | None = None

        if isinstance(rules_path, (list, tuple)):
            # Expect a list of tuples (name, content) or list of strings (content)
            self.rules_path = None
            self._rules = None
            self._rules_list = rules_path
            self._load_rules_from_list(rules_path)
        else:
            self.rules_path = Path(rules_path) if rules_path is not None else None
            self._rules = None
            self._load_rules()

    def _load_rules(self) -> None:
        """Compile all YARA rules from the rules directory using yara-python."""
        if not self.rules_path.exists():
            logger.warning(f"YARA rules path does not exist: {self.rules_path}")
            return

        yar_files = list(self.rules_path.glob("*.yar")) + list(
            self.rules_path.glob("*.yara")
        )
        if not yar_files:
            logger.warning(f"No .yar or .yara files found in {self.rules_path}")
            return

        try:
            filepaths = {f.stem: str(f) for f in yar_files}
            self._rules = yara.compile(filepaths=filepaths)
            self._source_count = len(yar_files)
            logger.info(
                f"Loaded {len(yar_files)} YARA rule files from {self.rules_path}"
            )
        except yara.Error as e:
            logger.error(f"Failed to compile YARA rules: {e}")
            self._rules = None

    def _load_rules_from_list(self, rules_list: list):
        """Compile YARA rules provided as list of contents.

        rules_list may be list of (name, content) tuples or list of strings.
        """
        try:
            # Compile multiple YARA sources separately using yara.compile(sources=...)
            if not rules_list:
                logger.warning("No YARA rules provided from DB")
                return

            sources_dict = {}
            idx = 0
            for item in rules_list:
                if isinstance(item, (list, tuple)):
                    name, content = item
                else:
                    name, content = None, item

                if not name:
                    name = f"db_rule_{idx}"
                # strip extension for namespace
                key = Path(name).stem
                sources_dict[key] = content
                idx += 1

            # Compile using sources mapping to avoid cross-file parsing issues
            self._rules = yara.compile(sources=sources_dict)
            self._source_count = len(sources_dict)
            logger.info(f"Compiled YARA rules from DB list, count={len(sources_dict)}")
        except yara.Error as e:
            logger.error(f"Failed to compile YARA rules from DB: {e}")
            self._rules = None

    @property
    def rules(self):
        """Return compiled rules for inspection."""
        return self._rules

    @property
    def rules_count(self) -> int:
        """Return the number of loaded rule files."""
        if self._rules is None:
            return 0

        # If rules were loaded from filesystem, return that count
        try:
            if self.rules_path is not None and self.rules_path.exists():
                yar_files = list(self.rules_path.glob("*.yar")) + list(
                    self.rules_path.glob("*.yara")
                )
                return len(yar_files)
        except Exception:
            # Ignore filesystem errors and fall back to source count
            pass

        # If rules were compiled from a list (DB), return the tracked source count
        return getattr(self, "_source_count", 0)

    def scan(self, parsed_logs: list[dict]) -> list[dict[str, Any]]:
        """Scan parsed logs against all loaded YARA rules.

        Args:
            parsed_logs: List of parsed log dictionaries from ApacheLogParser.
                        Each dict should have 'message', 'uri', 'user_agent',
                        'referer', 'raw', 'format' keys.

        Returns:
            List of match dictionaries with rule info and matched content.

        """
        if self._rules is None:
            logger.warning("YARA rules not loaded, skipping scan")
            return []

        results = []

        for i, log in enumerate(parsed_logs):
            scan_data = self._prepare_scan_data(log)

            if not scan_data:
                continue

            try:
                matches = self._rules.match(data=scan_data.encode("utf-8"))
                if matches:
                    logger.info(
                        f"Log {i} matched {len(matches)} rules: {[m.rule for m in matches]}"
                    )
                for match in matches:
                    matched_strings = []
                    for s in match.strings:
                        for inst in s.instances:
                            matched_strings.append(str(inst))

                    results.append(
                        {
                            "rule": match.rule,
                            "description": match.meta.get("description", ""),
                            "severity": match.meta.get("severity", "unknown"),
                            "category": match.meta.get("category", ""),
                            "mitre_ref": match.meta.get("mitre_ref", ""),
                            "matched_strings": matched_strings,
                            "log_index": i,
                            "matched_content": scan_data[:200],
                            "meta": match.meta,
                        }
                    )
            except Exception as e:
                logger.info(f"YARA scan error: {e}")

        return results

    def scan_raw(self, text: str) -> list[dict[str, Any]]:
        """Scan raw text against all loaded YARA rules (fallback method).

        Args:
            text: Raw text to scan.

        Returns:
            List of match dictionaries.

        """
        if self._rules is None:
            return []

        results = []

        try:
            matches = self._rules.match(data=text.encode("utf-8"))
            for match in matches:
                matched_strings = []
                for s in match.strings:
                    for inst in s.instances:
                        matched_strings.append(str(inst))

                results.append(
                    {
                        "rule": match.rule,
                        "description": match.meta.get("description", ""),
                        "severity": match.meta.get("severity", "unknown"),
                        "category": match.meta.get("category", ""),
                        "mitre_ref": match.meta.get("mitre_ref", ""),
                        "matched_strings": matched_strings,
                        "matched_content": text[:200],
                        "meta": match.meta,
                    }
                )
        except Exception as e:
            logger.info(f"YARA scan error: {e}")

        return results

    def reload(self, rules_list: list | None = None) -> None:
        """Reload YARA rules from DB or filesystem without recreating the engine.

        Args:
            rules_list: Optional list of (name, content) tuples from DB.
                        If None, reloads from the original source (filesystem or stored list).
        """
        if rules_list is not None:
            self._rules_list = rules_list
        if self.rules_path is not None:
            self._load_rules()
        elif self._rules_list is not None:
            self._load_rules_from_list(self._rules_list)
        else:
            logger.warning("No YARA rules source available for reload")

    @staticmethod
    def _prepare_scan_data(log: dict) -> str:
        """Prepare text data from parsed log for YARA scanning.

        For unknown formats, scan the raw line.
        For known formats, scan meaningful fields.
        """
        log_format = log.get("format", "unknown")

        if log_format == "unknown":
            return log.get("raw", "")

        parts = [
            log.get("message", ""),
            log.get("uri", ""),
            log.get("query", ""),
            log.get("user_agent", ""),
            log.get("referer", ""),
            log.get("client_ip", ""),
        ]

        return " ".join(filter(None, parts))
