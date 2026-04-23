"""Agent 3: Final report summarization with all detection contexts."""

import logging
import re

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from ..prompts import SUMMARIZER_SYSTEM_PROMPT, SUMMARIZER_USER_PROMPT

logger = logging.getLogger(__name__)


def create_agent3_chain(llm: BaseLanguageModel):
    """Create Agent 3 chain for final report summarization.

    Args:
        llm: LangChain language model

    Returns:
        RunnableSequence for final report generation

    """
    logger.info("Creating Agent 3 chain for final summarization")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SUMMARIZER_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(SUMMARIZER_USER_PROMPT),
        ]
    )

    chain = prompt | llm | StrOutputParser()

    logger.info("✓ Agent 3 chain created")
    return chain


def parse_agent3_metadata(report_text: str) -> dict:
    """Parse metadata from Agent 3 response.

    Args:
        report_text: Full response text with ---META--- block

    Returns:
        Dictionary with severity, threat_type, mitre_techniques,
        yara_rules, sigma_rules, events_found

    """
    severity_id = 3
    threat_id = 11
    mitre_techniques = []
    yara_rules = []
    sigma_rules = []
    events_found = 0

    try:
        if "---META---" in report_text:
            meta_start = report_text.index("---META---")
            meta_end = report_text.index("---END---", meta_start)
            meta_section = report_text[meta_start + 10 : meta_end].strip()

            for line in meta_section.split("\n"):
                line = line.strip()
                if ":" not in line:
                    continue

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "severity_level_id":
                    try:
                        severity_id = int(value)
                        if severity_id < 1 or severity_id > 4:
                            severity_id = 3
                    except ValueError:
                        pass

                elif key == "threat_type_id":
                    try:
                        threat_id = int(value)
                        if threat_id < 1 or threat_id > 11:
                            threat_id = 11
                    except ValueError:
                        pass

                elif key == "mitre_techniques":
                    mitre_techniques = re.findall(r'"([^"]*)"', value)

                elif key == "yara_rules":
                    yara_rules = re.findall(r'"([^"]*)"', value)

                elif key == "sigma_rules":
                    sigma_rules = re.findall(r'"([^"]*)"', value)

                elif key == "events_found":
                    try:
                        events_found = int(value)
                    except ValueError:
                        pass

            logger.debug(
                f"Parsed Agent 3 metadata: severity={severity_id}, threat={threat_id}, "
                f"mitre={mitre_techniques}, yara={yara_rules}, sigma={sigma_rules}"
            )

    except Exception as e:
        logger.warning(f"Failed to parse Agent 3 metadata: {e}")

    return {
        "severity_level_id": severity_id,
        "threat_type_id": threat_id,
        "mitre_techniques": mitre_techniques,
        "yara_rules": yara_rules,
        "sigma_rules": sigma_rules,
        "events_found": events_found,
    }


async def generate_final_report(
    llm,
    primary_analysis: str,
    events_found: int,
    mitre_context: str,
    agent2_report: str,
    severity_level_id: int,
    threat_type_id: int,
    mitre_techniques: list[str],
    yara_context: str,
    yara_count: int,
    sigma_context: str,
    sigma_count: int,
) -> dict:
    """Generate final report using Agent 3 chain.

    Args:
        llm: Language model
        primary_analysis: Primary analysis from Agent 1
        events_found: Number of events found by Agent 1
        mitre_context: MITRE ATT&CK context from RAG
        agent2_report: Detailed report from Agent 2
        severity_level_id: Severity level from Agent 2
        threat_type_id: Threat type from Agent 2
        mitre_techniques: List of MITRE technique IDs
        yara_context: Formatted YARA scan results
        yara_count: Number of YARA matches
        sigma_context: Formatted Sigma scan results
        sigma_count: Number of Sigma matches

    Returns:
        Dictionary with final report and metadata

    """
    chain = create_agent3_chain(llm)

    mitre_techniques_str = (
        ", ".join(mitre_techniques) if mitre_techniques else "Не определены"
    )

    result = await chain.ainvoke(
        {
            "primary_analysis": primary_analysis,
            "events_found": events_found,
            "mitre_context": mitre_context,
            "agent2_report": agent2_report,
            "severity_level_id": severity_level_id,
            "threat_type_id": threat_type_id,
            "mitre_techniques_str": mitre_techniques_str,
            "yara_context": yara_context,
            "yara_count": yara_count,
            "sigma_context": sigma_context,
            "sigma_count": sigma_count,
        }
    )

    report_text = result
    metadata = parse_agent3_metadata(report_text)

    # Remove metadata block from report
    if "---META---" in report_text:
        meta_start = report_text.index("---META---")
        report_text = report_text[:meta_start].strip()

    return {
        "final_report": report_text,
        **metadata,
    }
