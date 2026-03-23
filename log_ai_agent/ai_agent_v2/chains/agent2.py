"""Agent 2: Final report generation chain with metadata extraction."""

import logging
import re
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

# System prompt for Agent 2
SYSTEM_PROMPT = """Ты - старший эксперт по кибербезопасности и анализу инцидентов.
Твоя задача - на основе первичного анализа логов и данных из базы знаний MITRE ATT&CK:
- Определить тип угрозы (threat_type_id: 1-11)
- Оценить уровень серьезности (severity_level_id: 1-4)
- Сопоставить обнаруженные активности с техниками MITRE ATT&CK
- Сформировать подробный итоговый отчёт
- Дать практические рекомендации по устранению

Шкала серьезности:
1 - Критический: активная атака, утечка данных, компрометация системы
2 - Высокий: попытка атаки, подозрительная активность, требующая внимания
3 - Средний: единичные аномалии, потенциальные риски
4 - Низкий: незначительные отклонения, информационные события

Типы угроз:
1 - Вторжение
2 - Вредоносное ПО
3 - DDoS
4 - Утечка данных
5 - Несанкционированный доступ
6 - Фишинг
7 - SQL-инъекция
8 - XSS
9 - Брутфорс
10 - Сканирование портов
11 - Другое

Требования к ответу:
- Отвечай на русском языке
- Структурируй отчёт в markdown
- Давай конкретные рекомендации
- Ссылайся на техники MITRE ATT&CK когда уместно

ВАЖНО: В конце ответа добавь блок метаданных в формате:
---META---
severity_level_id: <число 1-4>
threat_type_id: <число 1-11>
mitre_techniques: ["<ID техники>", ...]
---END---"""

# User prompt template
USER_PROMPT = """На основе первичного анализа логов и данных из MITRE ATT&CK сформируй итоговый отчёт.

ПЕРВИЧНЫЙ АНАЛИЗ:
{primary_analysis}

ТЕХНИКИ MITRE ATT&CK (найденные по ключевым словам):
{mitre_context}

ЗАДАЧА:
1. Определи тип угрозы (threat_type_id: 1-11)
2. Оцени уровень серьезности (severity_level_id: 1-4)
3. Сопоставь обнаруженные активности с техниками MITRE ATT&CK
4. Сформируй подробный отчёт
5. Дай практические рекомендации по устранению

ФОРМАТ ОТВЕТА:
## Отчёт об инциденте безопасности

### Описание инцидента
Подробное описание того что произошло.

### Сопоставление с MITRE ATT&CK
- **Тактика**: [название]
- **Техники**: [ID и название]
- **Линия защиты**: [1/2/3]

### Уровень серьезности
[Обоснование выбора severity]

### Тип угрозы
[Обоснование выбора threat_type]

### Рекомендации
- [Конкретные шаги по устранению]
- [Меры по предотвращению]

---META---
severity_level_id: <число 1-4>
threat_type_id: <число 1-11>
mitre_techniques: ["<ID техники>", ...]
---END---"""


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
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(USER_PROMPT),
        ]
    )

    # Create chain using RunnableSequence (new API)
    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("✓ Agent 2 chain created")
    return chain


def parse_metadata(report_text: str) -> dict[str, Any]:
    """Parse metadata from Agent 2 response.

    Args:
        report_text: Full response text

    Returns:
        Dictionary with severity, threat_type, mitre_techniques

    """
    severity_id = 3  # Default: Medium
    threat_id = 11  # Default: Other
    mitre_techniques = []

    try:
        # Look for ---META--- block
        if "---META---" in report_text:
            meta_start = report_text.index("---META---")
            meta_end = report_text.index("---END---", meta_start)
            meta_section = report_text[meta_start + 10 : meta_end].strip()

            for line in meta_section.split("\n"):
                line = line.strip()
                if ":" in line:
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
                        # Parse JSON-like array
                        try:
                            mitre_techniques = re.findall(r'"([^"]+)"', value)
                        except Exception:
                            pass

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
) -> dict[str, Any]:
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
