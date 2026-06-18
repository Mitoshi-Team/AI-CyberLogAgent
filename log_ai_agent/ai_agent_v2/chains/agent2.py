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
        Dictionary with overall_severity and incidents list

    """
    overall_severity = 3
    incidents = []

    try:
        if "---META---" in report_text:
            meta_start = report_text.index("---META---")
            meta_end = report_text.index("---END---", meta_start)
            meta_section = report_text[meta_start + 10 : meta_end].strip()

            # Split by ---INCIDENT--- delimiter
            parts = re.split(r"^---INCIDENT---$", meta_section, flags=re.MULTILINE)

            # First part is global metadata
            global_part = parts[0].strip() if parts else ""
            for line in global_part.split("\n"):
                line = line.strip()
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "overall_severity":
                    try:
                        overall_severity = int(value)
                        if overall_severity < 1 or overall_severity > 4:
                            overall_severity = 3
                    except ValueError:
                        pass

            # Remaining parts are incidents
            for incident_part in parts[1:]:
                incident = {}
                for line in incident_part.strip().split("\n"):
                    line = line.strip()
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "description":
                        incident["description"] = value
                    elif key == "technique_id":
                        incident["technique_id"] = value
                    elif key == "technique_name":
                        incident["technique_name"] = value
                    elif key == "tactic":
                        incident["tactic"] = value
                    elif key == "severity_level_id":
                        try:
                            incident["severity_level_id"] = int(value)
                        except ValueError:
                            incident["severity_level_id"] = 3

                if incident.get("technique_id"):
                    incident.setdefault("severity_level_id", 3)
                    incidents.append(incident)

            logger.debug(
                f"Parsed metadata: overall_severity={overall_severity}, incidents={len(incidents)}"
            )

    except Exception as e:
        logger.warning(f"Failed to parse metadata: {e}")

    return {
        "overall_severity": overall_severity,
        "incidents": incidents,
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
        "overall_severity": metadata.get("overall_severity", 3),
        "incidents": metadata.get("incidents", []),
    }
