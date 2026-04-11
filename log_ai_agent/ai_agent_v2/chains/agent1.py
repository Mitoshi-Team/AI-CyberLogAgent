"""Agent 1: Primary log analysis chain."""

import logging

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence

from ..prompts import PRIMARY_ANALYSIS_SYSTEM_PROMPT, PRIMARY_ANALYSIS_USER_PROMPT

logger = logging.getLogger(__name__)


def create_agent1_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Agent 1 chain for primary log analysis.

    Args:
        llm: LangChain language model (e.g., GigaChat)

    Returns:
        RunnableSequence for primary analysis

    """
    logger.info("Creating Agent 1 chain for primary log analysis")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(PRIMARY_ANALYSIS_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(PRIMARY_ANALYSIS_USER_PROMPT),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("✓ Agent 1 chain created")
    return chain


async def analyze_logs_primary(
    llm: BaseLanguageModel,
    log_content: str,
) -> dict:
    """Analyze logs using Agent 1 chain.

    Args:
        llm: Language model
        log_content: Raw log content

    Returns:
        Dictionary with primary analysis

    """
    chain = create_agent1_chain(llm)
    result = await chain.ainvoke({"log_content": log_content})

    return {
        "primary_analysis": result,
        "events_found": result.count("### Событие"),
    }
