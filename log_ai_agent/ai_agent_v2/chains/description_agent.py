"""Description Agent: Generate descriptions for event groups."""
import json
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

from ..models_types import EventGroup, GroupDescription

logger = logging.getLogger(__name__)

DESCRIPTION_AGENT_SYSTEM_PROMPT = """Ты — эксперт по анализу событий безопасности.
Твоя задача — генерировать связные описания для групп подозрительных событий.

Для каждой группы создай ОДНО описание, которое:
- Объединяет все события в группе
- Указывает характер угрозы (брутфорс, SQL-инъекция и т.д.)
- Включает ключевые индикаторы (IP, пользователь, путь и т.д.)
- Сохраняет временные рамки

Примеры:
- "Серия из 15 неудачных попыток SSH-аутентификации для пользователя admin с IP 89.23.74.19"
- "Подозрительные POST-запросы к /admin/login с паттернами SQL-инъекции"
- "Множественные попытки доступа к конфиденциальным файлам с IP 192.168.1.50"

Будь конкретным и информативным. Описание должно помочь в поиске MITRE ATT&CK."""


DESCRIPTION_AGENT_USER_PROMPT = """Сгенерируй связное описание и ключевые слова для группы событий.

ГРУППА:
- ID: {group_id}
- Время: {first_seen} - {last_seen}
- Событий в группе: {events_count}

СОБЫТИЯ:
{events}

ЗАДАЧА:
Создай одно связное описание и список ключевых слов для RAG-поиска.

ОПИСАНИЕ:
- Объедини все события в группе
- Включи характер активности (брутфорс, инъекция и т.д.)
- Добавь ключевые индикаторы (IP, пользователь, путь и т.д.)
- Укажи масштаб и временные рамки
- Стиль: "Обнаружено...", "Зафиксировано..." (минимум 100 символов)

КЛЮЧЕВЫЕ СЛОВА:
- 5-10 терминов для поиска в MITRE ATT&CK
- Включи: тип атаки, инструменты, техники, индикаторы, команды, имена файлов/процессов
- На русском языке

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО JSON:
{{"description": "твоё подробное описание здесь (мин. 100 символов)", "keywords": ["слово1", "слово2", ...], "first_seen": "{first_seen}", "last_seen": "{last_seen}", "group_id": "{group_id}"}}

НЕ добавляй дополнительный текст."""


def create_description_agent_chain(llm: BaseLanguageModel) -> RunnableSequence:
    """Create Description Agent chain for group description generation.

    Args:
        llm: LangChain language model

    Returns:
        RunnableSequence for description generation

    """
    logger.info("Creating Description Agent chain")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(DESCRIPTION_AGENT_SYSTEM_PROMPT),
            HumanMessagePromptTemplate.from_template(DESCRIPTION_AGENT_USER_PROMPT),
        ]
    )

    chain: RunnableSequence = prompt | llm | StrOutputParser()

    logger.info("Description Agent chain created")
    return chain


def parse_description_response(response: str, group_id: str, first_seen: str, last_seen: str) -> GroupDescription | None:
    """Parse description and keywords from Description Agent response.

    Args:
        response: LLM response
        group_id: Original group ID
        first_seen: Group first timestamp
        last_seen: Group last timestamp

    Returns:
        GroupDescription or None if parsing failed

    """
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            data = json.loads(json_match.group())
            description = data.get("description", response[:200])
            keywords = data.get("keywords", data.get("keywords_ru", []))

            # Fallback for description from LLM response if not in JSON
            if not description or len(description) < 50:
                # Try to extract description from the raw response
                desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', response)
                if desc_match:
                    description = desc_match.group(1)

            return GroupDescription(
                group_id=group_id,
                description=description if description else response[:300],
                first_seen=first_seen,
                last_seen=last_seen,
                keywords=keywords if isinstance(keywords, list) else [],
            )
        except json.JSONDecodeError:
            pass

    return GroupDescription(
        group_id=group_id,
        description=response[:300] if response else "No description",
        first_seen=first_seen,
        last_seen=last_seen,
        keywords=[],
    )


async def generate_group_descriptions(
    llm: BaseLanguageModel,
    groups: list[EventGroup],
) -> list[GroupDescription]:
    """Generate descriptions for all event groups in parallel.

    Args:
        llm: Language model
        groups: List of EventGroup from Agent1

    Returns:
        List of GroupDescription for each group

    """
    if not groups:
        return []

    chain = create_description_agent_chain(llm)

    logger.info(f"Description Agent: generating descriptions for {len(groups)} groups")

    async def process_group(group: EventGroup) -> GroupDescription:
        events = group.get("events", [])
        events_text = "\n".join([
            f"- [{e.get('timestamp', 'N/A')}] {e.get('description', '')}"
            for e in events
        ])

        result = await chain.ainvoke({
            "group_id": group.get("group_id", ""),
            "first_seen": group.get("first_seen", ""),
            "last_seen": group.get("last_seen", ""),
            "events_count": len(events),
            "events": events_text,
        })

        return parse_description_response(
            result,
            group.get("group_id", ""),
            group.get("first_seen", ""),
            group.get("last_seen", ""),
        )

    descriptions = await asyncio.gather(*[process_group(g) for g in groups])

    logger.info(f"Description Agent: generated {len(descriptions)} descriptions")
    return list(descriptions)


import asyncio