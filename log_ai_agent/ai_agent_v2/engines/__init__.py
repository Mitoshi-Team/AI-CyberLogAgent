"""Engines package for YARA and Sigma rule-based detection.

Provides adapted engines for log text analysis:
- YaraEngine: Parses YARA .yar files, applies regex patterns to log text
- SigmaEngine: Parses Sigma YAML rules, applies pattern matching to log text
"""

from .sigma_engine import SigmaEngine
from .yara_engine import YaraEngine

__all__ = ["SigmaEngine", "YaraEngine"]
