"""Agent 1: Primary log analysis chain."""

import logging
from typing import Any

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.runnables import RunnableSequence

logger = logging.getLogger(__name__)

# System prompt for Agent 1
SYSTEM_PROMPT = """Ты - эксперт по анализу логов и кибербезопасности.
Твоя задача - анализировать сырые логи и выявлять:
- Подозрительные активности и аномалии
- Паттерны атак
- Ошибки и сбои в работе системы
- Признаки компрометации

Требования к ответу:
- Будь конкретным, ссылайся на конкретные строки лога
- Выделяй только значимые события, игнорируй шум
- Группируй похожие события
- Описывай что произошло, когда и какие признаки указывают на проблему
- Не делай финальных выводов о типе угрозы - это задача второго агента

Формат ответа - структурированный отчёт в markdown."""

# User prompt template
USER_PROMPT = """Проанализируй следующий лог-файл на предмет подозрительной активности.

ЛОГ-ФАЙЛ:
```
{log_content}
```

ЗАДАЧА:
1. Выяви все подозрительные активности, ошибки и аномалии
2. Определи временные рамки событий
3. Выдели конкретные строки лога которые указывают на проблемы
4. Сгруппируй похожие события
5. Опиши что произошло в каждом случае

ФОРМАТ ОТВЕТА:
## Обнаруженные события

### Событие 1: [название]
- **Время**: [timestamp если есть]
- **Описание**: что произошло
- **Индикаторы**: конкретные строки из лога
- **Признаки**: почему это подозрительно

### Событие 2: [название]
...

## Итог
Краткое резюме всех обнаруженных подозрительных активностей."""


def create_agent1_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Agent 1 chain for primary log analysis.

    Args:
        llm: LangChain language model (e.g., GigaChat)

    Returns:
        RunnableSequence for primary analysis

    """
    logger.info("Creating Agent 1 chain for primary log analysis")

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(USER_PROMPT),
        ]
    )

    # Create chain using RunnableSequence (new API, no deprecation)
    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("✓ Agent 1 chain created")
    return chain


async def analyze_logs_primary(
    llm: BaseLanguageModel,
    log_content: str,
) -> dict[str, Any]:
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
