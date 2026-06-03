"""YARA rule generator and validator.

Generates YARA rules for MITRE ATT&CK techniques that were found by RAG
but not covered by existing YARA rules. Validates generated rules through
compilation, log scanning, and LLM review.
"""

import logging
import re
from pathlib import Path
from typing import Any

import yara
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..knowledge_base.manager import ChromaDBManager
from ..models_types import EventGroup, MITRETechnique
from ..prompts.yara_generation import (
    YARA_FIX_PROMPT,
    YARA_GENERATION_SYSTEM_PROMPT,
    YARA_GENERATION_USER_PROMPT,
    YARA_REVIEW_SYSTEM_PROMPT,
    YARA_REVIEW_USER_PROMPT,
)
from ..parsers.apache_parser import ParsedLog

logger = logging.getLogger(__name__)

# Default example rule shown to LLM for style reference
_DEFAULT_EXAMPLE_RULE = """rule SQL_Injection_Advanced
{
    meta:
        description = "Detects advanced SQL injection attempts"
        author = "AI CyberLog Agent"
        severity = "high"
        category = "initial_access"
        mitre_ref = "T1190"

    strings:
        $s1 = "UNION" nocase fullword
        $s2 = "SELECT" nocase fullword
        $s3 = "INSERT" nocase fullword
        $l1 = "OR 1=1" nocase
        $e1 = "UNION%20SELECT" nocase

    condition:
        ($s1 and $s2) or any of ($l*) or any of ($e*) or 2 of ($s*)
}"""


class GeneratedYaraRule:
    """Represents a generated and validated YARA rule."""

    def __init__(
        self,
        rule_name: str,
        rule_content: str,
        technique_id: str,
        technique_name: str,
    ):
        self.rule_name = rule_name
        self.rule_content = rule_content
        self.technique_id = technique_id
        self.technique_name = technique_name
        self.validation_errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "rule_content": self.rule_content,
            "technique_id": self.technique_id,
            "technique_name": self.technique_name,
        }


def _sanitize_rule_name(name: str) -> str:
    """Convert arbitrary text to a valid YARA rule name."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_")
    if not sanitized or sanitized[0].isdigit():
        sanitized = "rule_" + sanitized
    return sanitized[:64]


def _extract_rule_name(content: str) -> str | None:
    """Extract rule name from YARA rule content."""
    match = re.search(r"^\s*rule\s+(\w+)", content, re.MULTILINE)
    return match.group(1) if match else None


def _strip_yara_markers(text: str) -> str:
    """Remove ```yara or ``` markers from LLM output."""
    text = re.sub(r"^```yara\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    return text.strip()


class YaraGenerator:
    """Generates, validates, and manages YARA rules for uncovered techniques."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        chroma_mgr: ChromaDBManager | None = None,
        example_rule: str | None = None,
        max_retries: int = 2,
    ):
        self.llm = llm
        self.chroma_mgr = chroma_mgr
        self.example_rule = example_rule or _DEFAULT_EXAMPLE_RULE
        self.max_retries = max_retries
        self._generation_chain = self._build_generation_chain()
        self._fix_chain = self._build_fix_chain()
        self._review_chain = self._build_review_chain()

    def _build_generation_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(YARA_GENERATION_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(YARA_GENERATION_USER_PROMPT),
        ])
        return prompt | self.llm | StrOutputParser()

    def _build_fix_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "Ты — эксперт по YARA. Исправь ошибку в правиле."
            ),
            HumanMessagePromptTemplate.from_template(YARA_FIX_PROMPT),
        ])
        return prompt | self.llm | StrOutputParser()

    def _build_review_chain(self):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(YARA_REVIEW_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(YARA_REVIEW_USER_PROMPT),
        ])
        return prompt | self.llm | StrOutputParser()

    def _get_technique_description(self, technique_id: str) -> str:
        """Retrieve technique description from ChromaDB if available."""
        if not self.chroma_mgr or not self.chroma_mgr.is_initialized:
            return ""
        try:
            results = self.chroma_mgr.search(
                query=f"technique_id: {technique_id}",
                k=1,
                score_threshold=0.0,
                filter_dict={"technique_id": technique_id},
            )
            if results:
                content = results[0].get("content", "")
                if content.startswith("passage: "):
                    content = content[len("passage: "):]
                return content[:1000]
        except Exception as e:
            logger.warning(f"Failed to get technique description for {technique_id}: {e}")
        return ""

    @staticmethod
    def _compile_rule(name: str, content: str) -> bool:
        """Try compiling a YARA rule. Returns True if valid."""
        try:
            yara.compile(sources={name: content})
            return True
        except yara.Error:
            return False

    @staticmethod
    def _scan_logs(rule_content: str, rule_name: str, log_lines: list[str]) -> bool:
        """Check if compiled rule matches at least one of the log lines."""
        try:
            rules = yara.compile(sources={rule_name: rule_content})
            for line in log_lines:
                matches = rules.match(data=line.encode("utf-8"))
                if matches:
                    return True
            return False
        except yara.Error:
            return False

    async def generate(
        self,
        technique: MITRETechnique,
        group: EventGroup | None = None,
        parsed_logs: list[ParsedLog] | None = None,
    ) -> GeneratedYaraRule | None:
        """Generate a YARA rule for a specific technique.

        Args:
            technique: MITRE technique that needs YARA coverage
            group: The original event group (for log lines)
            parsed_logs: All parsed logs (for fallback log extraction)

        Returns:
            GeneratedYaraRule or None if generation/validation failed

        """
        technique_id = technique.get("technique_id", "unknown")
        technique_name = technique.get("name", "Unknown")
        group_id = technique.get("group_id", "")

        # Collect log lines from the group
        log_lines: list[str] = []
        if group:
            log_lines = group.get("log_lines", [])
        if not log_lines and parsed_logs:
            for pl in parsed_logs:
                raw = pl.get("raw", "")
                if raw:
                    log_lines.append(raw)

        if not log_lines:
            logger.warning(
                f"[YaraGen] No log lines for technique {technique_id}, skipping"
            )
            return None

        # Get technique description from ChromaDB
        technique_description = self._get_technique_description(technique_id)
        if not technique_description:
            technique_description = technique_name

        # Format log lines for prompt (max 20 lines to avoid token overflow)
        log_lines_text = "\n".join(log_lines[:20])
        if len(log_lines) > 20:
            log_lines_text += f"\n[... {len(log_lines) - 20} more lines ...]"

        # --- GENERATION ---
        logger.info(f"[YaraGen] Generating rule for {technique_id} ({technique_name})")
        rule_name_base = _sanitize_rule_name(f"{technique_id}_{technique_name}")
        raw_rule = rule_name_base
        last_error = ""

        for attempt in range(self.max_retries + 1):
            try:
                if attempt == 0:
                    result = await self._generation_chain.ainvoke({
                        "technique_id": technique_id,
                        "technique_name": technique_name,
                        "technique_description": technique_description,
                        "log_lines": log_lines_text,
                        "example_rule": self.example_rule,
                    })
                else:
                    result = await self._fix_chain.ainvoke({
                        "error": last_error,
                        "rule_content": raw_rule,
                    })

                raw_rule = _strip_yara_markers(result)
                rule_name = _extract_rule_name(raw_rule) or rule_name_base

                # --- VALIDATION STEP 1: Compilation ---
                if not self._compile_rule(rule_name, raw_rule):
                    last_error = "YARA compilation error: invalid syntax"
                    logger.warning(
                        f"[YaraGen] Attempt {attempt + 1}: compilation failed for {rule_name}"
                    )
                    continue

                # --- VALIDATION STEP 2: Scan original logs ---
                if not self._scan_logs(raw_rule, rule_name, log_lines):
                    last_error = "Rule did not match any of the provided log lines"
                    logger.warning(
                        f"[YaraGen] Attempt {attempt + 1}: no log match for {rule_name}"
                    )
                    continue

                # --- VALIDATION STEP 3: LLM review ---
                review = await self._review_chain.ainvoke({
                    "rule_content": raw_rule,
                    "log_lines": log_lines_text,
                })

                if review and not re.search(r'\bVALID\b', review.strip().upper()):
                    last_error = f"LLM review: {review[:200]}"
                    logger.warning(
                        f"[YaraGen] Attempt {attempt + 1}: review failed for {rule_name}: {last_error}"
                    )
                    continue

                # All validations passed
                rule = GeneratedYaraRule(
                    rule_name=rule_name,
                    rule_content=raw_rule,
                    technique_id=technique_id,
                    technique_name=technique_name,
                )
                logger.info(
                    f"[YaraGen] Successfully generated rule '{rule_name}' for {technique_id}"
                )
                return rule

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[YaraGen] Attempt {attempt + 1} error for {technique_id}: {e}"
                )

        logger.warning(
            f"[YaraGen] Failed to generate valid rule for {technique_id} "
            f"after {self.max_retries + 1} attempts: {last_error}"
        )
        return None

    async def generate_for_pipeline(
        self,
        pipeline_stages: dict[str, Any],
        groups: list[EventGroup],
        parsed_logs: list[ParsedLog],
    ) -> list[GeneratedYaraRule]:
        """Generate YARA rules for MITRE techniques not covered by existing YARA rules.

        Args:
            pipeline_stages: The 'stages' dict from pipeline results
            groups: Event groups from Agent 1 (for log line extraction)
            parsed_logs: Parsed logs (for fallback)

        Returns:
            List of valid GeneratedYaraRule objects

        """
        rag_stage = pipeline_stages.get("agent2", {})
        yara_stage = pipeline_stages.get("yara", {})

        mitre_techniques: list[MITRETechnique] = rag_stage.get("mitre_techniques", [])
        yara_rules_matched: list[str] = yara_stage.get("rules_matched", [])

        if not mitre_techniques:
            logger.info("[YaraGen] No MITRE techniques found by RAG, skipping generation")
            return []

        if yara_rules_matched:
            logger.info(
                f"[YaraGen] YARA already matched {len(yara_rules_matched)} rules, "
                f"skipping generation"
            )
            return []

        logger.info(
            f"[YaraGen] Generating rules for {len(mitre_techniques)} "
            f"uncovered techniques"
        )

        generated: list[GeneratedYaraRule] = []
        for technique in mitre_techniques:
            group_id = technique.get("group_id", "")
            group = next(
                (g for g in groups if g.get("group_id") == group_id),
                None,
            )
            rule = await self.generate(
                technique=technique,
                group=group,
                parsed_logs=parsed_logs,
            )
            if rule:
                generated.append(rule)

        logger.info(
            f"[YaraGen] Generated {len(generated)}/{len(mitre_techniques)} valid rules"
        )
        return generated
