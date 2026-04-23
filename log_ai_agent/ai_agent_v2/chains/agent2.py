"""Agent 2: Final report generation chain with metadata extraction."""

import logging
import re

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence

from ..prompts import FINAL_REPORT_SYSTEM_PROMPT, FINAL_REPORT_USER_PROMPT

logger = logging.getLogger(__name__)


def create_agent2_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Agent 2 chain for final report generation.

    Args:
        llm: LangChain language model

    Returns:
        RunnableSequence for final report

    """
    logger.info("Creating Agent 2 chain for final report generation")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(FINAL_REPORT_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(FINAL_REPORT_USER_PROMPT),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("✓ Agent 2 chain created")
    return chain


def parse_metadata(report_text: str) -> dict:
    """Parse metadata from Agent 2 response.

    Args:
        report_text: Full response text

    Returns:
        Dictionary with severity, threat_type, mitre_techniques

    """
    severity_id = 3
    threat_id = 11
    mitre_techniques = []

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
                    mitre_techniques = re.findall(r'"([^"]+)"', value)

            logger.debug(
                f"Parsed metadata: severity={severity_id}, threat={threat_id}, mitre={mitre_techniques}"
            )

    except Exception as e:
        logger.warning(f"Failed to parse metadata: {e}")

    return {
        "severity_level_id": severity_id,
        "threat_type_id": threat_id,
        "mitre_techniques": mitre_techniques,
    }


async def generate_final_report(
    llm: BaseLanguageModel,
    primary_analysis: str,
    mitre_context: str,
) -> dict:
    """Generate final report using Agent 2 chain.

    Args:
        llm: Language model
        primary_analysis: Primary analysis from Agent 1
        mitre_context: MITRE context from RAG

    Returns:
        Dictionary with final report and metadata

    """
    chain = create_agent2_chain(llm)

    result = await chain.ainvoke(
        {
            "primary_analysis": primary_analysis,
            "mitre_context": mitre_context,
        }
    )

    report_text = result
    metadata = parse_metadata(report_text)

    # Remove metadata block from report
    if "---META---" in report_text:
        meta_start = report_text.index("---META---")
        report_text = report_text[:meta_start].strip()

    return {
        "final_report": report_text,
        **metadata,
    }
