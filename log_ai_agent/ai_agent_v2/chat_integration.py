import logging

import asyncpg
from langchain_core.messages import HumanMessage, SystemMessage

from .chains.llm import create_gigachat_llm

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = """Ты - AI-ассистент по кибербезопасности в системе AI CyberLog Agent.
Отвечай на русском языке, по существу и с практическими рекомендациями.

Правила ответа:
- Используй контекст диалога и данные последнего отчета, если они доступны.
- Если данных для точного вывода недостаточно, явно укажи это и предложи следующий шаг.
- Не выдумывай факты, которых нет в переданных данных.
- Формулируй ответ как нормальный диалоговый ответ ассистента, без служебных меток.
"""


def _extract_llm_text(result: object) -> str:
    """Normalize LangChain LLM output into plain text."""
    content = getattr(result, "content", result)

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(p.strip() for p in parts if p and p.strip())

    return str(content).strip()


async def _generate_agent_response(
    conn: asyncpg.Connection,
    user_id: int,
    user_message: str,
) -> str:
    """Generate chat response via LLM using recent conversation and latest report."""
    history_rows = await conn.fetch(
        """
        SELECT role, content, created_at
        FROM public."Messages"
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 10
        """,
        user_id,
    )

    latest_report = await conn.fetchrow(
        """
        SELECT r.report_id, r.description, r.created_at
        FROM public."Reports" r
        ORDER BY r.created_at DESC
        LIMIT 1
        """
    )

    history_lines: list[str] = []
    for row in reversed(history_rows):
        role = "Пользователь" if row["role"] == "user" else "Агент"
        history_lines.append(
            f"[{row['created_at'].isoformat()}] {role}: {row['content']}"
        )

    history_text = "\n".join(history_lines) if history_lines else "История отсутствует"

    if latest_report:
        report_context = (
            f"ID: {latest_report['report_id']}\n"
            f"Время: {latest_report['created_at'].isoformat()}\n"
            f"Описание:\n{latest_report['description']}"
        )
    else:
        report_context = "Отчеты пока отсутствуют"

    llm = create_gigachat_llm()
    llm_result = await llm.ainvoke(
        [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "Контекст последнего отчета:\n"
                    f"{report_context}\n\n"
                    "История диалога (последние 10 сообщений):\n"
                    f"{history_text}\n\n"
                    "Текущее сообщение пользователя:\n"
                    f"{user_message}\n\n"
                    "Сформируй полезный ответ ассистента."
                )
            ),
        ]
    )

    response = _extract_llm_text(llm_result)
    if not response:
        raise RuntimeError("LLM returned empty response")

    return response


async def clear_user_context(user_id: int, database_url: str) -> int:
    """Clear all chat messages for a user and return deleted row count."""
    conn = await asyncpg.connect(database_url, timeout=10)
    try:
        result = await conn.execute(
            'DELETE FROM public."Messages" WHERE user_id = $1',
            user_id,
        )
        try:
            return int(result.split()[-1])
        except Exception:
            return 0
    finally:
        await conn.close()


async def process_chat_message(
    user_id: int, user_message: str, database_url: str
) -> dict:
    """Process user chat message and save user/agent messages."""
    message = (user_message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty")

    conn = await asyncpg.connect(database_url, timeout=10)
    try:
        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "user",
            message,
        )

        response = await _generate_agent_response(
            conn=conn,
            user_id=user_id,
            user_message=message,
        )
        mode = "agent_llm"

        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "agent",
            response,
        )

        return {"response": response, "mode": mode}
    finally:
        await conn.close()
