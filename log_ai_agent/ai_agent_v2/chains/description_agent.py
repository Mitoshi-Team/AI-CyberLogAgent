"""Description Agent: Generate descriptions for event groups."""
import asyncio
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

DESCRIPTION_AGENT_SYSTEM_PROMPT = """Ты — эксперт по анализу событий безопасности с фокусом на техники MITRE ATT&CK.

Твоя задача — генерировать точные, детализированные описания для групп подозрительных событий.

ВАЖНО: Твои описания должны помогать идентифицировать следующие категории атак:

1. ВЫПОЛНЕНИЕ КОДА (Execution):
   - PowerShell / cmd / bash / wmic / mshta
   - Запуск скриптов, скачивание и выполнение
   - Использование WMI, планировщика задач

2. ПЕРСИСТЕНЦИЯ (Persistence):
   - Создание служб (sc.exe, new-service)
   - Изменение автозагрузки (Run, RunOnce, Startup folder)
   - Планировщик задач (schtasks)

3. ПОВЫШЕНИЕ ПРИВИЛЕГИЙ (Privilege Escalation):
   - BypassUAC, использование уязвимостей
   - Перехват токенов, sudo

4. ОБХОД ЗАЩИТЫ (Defense Evasion):
   - Отключение AV/EDR, изменение политик
   - Инжекция в процессы (CreateRemoteThread, QueueUserAPC)
   - Обфускация, исполнение из памяти

5. ДОСТУП К УЧЁТНЫМ ДАННЫМ (Credential Access):
   - Дамп LSASS (MiniDump, procdump)
   - Выгрузка SAM/ntds.dit
   - Mimikatz, ключевые API вызовы

ЧЕГО ИЗБЕГАТЬ:
- Общих фраз: "подозрительная активность", "аномальное поведение"
- Сведения всего к "сканированию", "разведке" или "DoS"
- Если в логах есть конкретные команды или API-вызовы — описывай ИХ, а не гипотетические угрозы

Примеры КАЧЕСТВЕННЫХ описаний:
- "Обнаружено создание службы 'UpdateService' через sc.exe с последующим запуском PowerShell с закодированной командой"
- "Зафиксирована модификация реестра в HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run для персистенции"
- "Выявлен дамп LSASS с помощью comsvcs.dll: rundll32.exe C:\\Windows\\System32\\comsvcs.dll MiniDump <PID> lsass.dmp"
- "Обнаружена загрузка и выполнение PowerShell-скрипта из внешнего домена через IEX (New-Object Net.WebClient).DownloadString()"
- "Зафиксирован процесс инжекции в svchost.exe через OpenProcess → VirtualAllocEx → CreateRemoteThread"
"""

DESCRIPTION_AGENT_USER_PROMPT = """Сгенерируй связное описание и ключевые слова для группы подозрительных строк логов.

ГРУППА:
- ID: {group_id}
- Время: {first_seen} - {last_seen}
- Строк логов в группе: {log_lines_count}

СТРОКИ ЛОГОВ:
{log_lines}

ЗАДАЧА:
Создай одно связное описание и список ключевых слов для RAG-поиска в MITRE ATT&CK.

ОПИСАНИЕ (мин. 150 символов):
- Объедини все строки логов в единое описание атаки
- Укажи конкретные команды, пути, процессы, аргументы
- Отрази технику из MITRE ATT&CK (если очевидно)
- Стиль: "Обнаружено...", "Зафиксировано..."

КЛЮЧЕВЫЕ СЛОВА:
- 5-10 терминов
- Используй РУССКИЕ keywords из базы MITRE

ПРАВИЛА ВЫБОРА KEYWORDS:
Проанализируй команды, утилиты, аргументы и системные вызовы в логах группы.
Сгенерируй keywords, которые максимально точно описывают суть активности:
- названия утилит (reg.exe, vssadmin, nmap, sc.exe, certutil, cscript, wmic, rundll32, curl, ssh, etc.)
- типы активности (дамп учетных данных, сканирование сети, создание службы, выполнение скрипта, персистенция, обход UAC, инжекция процесса, модификация реестра, сбор информации, и т.д.)
- ID техник MITRE ATT&CK, если уверен

НЕ ограничивайся заранее известным списком — анализируй контекст каждой строки и экстраполируй.
Например, если видишь reg.exe save — это может быть дамп учетных данных (T1003), а не просто работа с реестром.

ИСКЛЮЧЕНИЯ (НЕ добавляй keywords):
- HTTP методы DELETE, PUT, PATCH — это шум, не атака
- HTTP 5xx ошибки (500, 502, 503, 504) — это шум, не атака
- Легитимные команды (sudo, systemctl, docker, kubectl) без других признаков атаки

ВАЖНО: 
- Добавляй ТОЛЬКО те keywords, которые соответствуют реальным командам в логах
- Если сомневаешься — оставь keywords пустыми []

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО JSON:
{{"description": "твоё подробное описание здесь (мин. 150 символов)", "keywords": ["keyword1", "keyword2", ...], "first_seen": "{first_seen}", "last_seen": "{last_seen}", "group_id": "{group_id}"}}

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

    semaphore = asyncio.Semaphore(3)

    async def process_group(group: EventGroup) -> GroupDescription:
        async with semaphore:
            log_lines = group.get("log_lines", [])
            log_lines_text = "\n".join(log_lines)

            result = await chain.ainvoke({
                "group_id": group.get("group_id", ""),
                "first_seen": group.get("first_seen", ""),
                "last_seen": group.get("last_seen", ""),
                "log_lines_count": len(log_lines),
                "log_lines": log_lines_text,
            })

            return parse_description_response(
                result,
                group.get("group_id", ""),
                group.get("first_seen", ""),
                group.get("last_seen", ""),
            )

    results = await asyncio.gather(
        *[process_group(g) for g in groups],
        return_exceptions=True,
    )

    descriptions: list[GroupDescription] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.warning(
                f"Description Agent: group {groups[i].get('group_id', i)} failed: {r}"
            )
        else:
            descriptions.append(r)

    logger.info(f"Description Agent: generated {len(descriptions)}/{len(groups)} descriptions")
    return descriptions