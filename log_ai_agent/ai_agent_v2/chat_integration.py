import logging

import asyncpg

logger = logging.getLogger(__name__)


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
    """Process user chat message and save user/agent messages.

    This integration is pipeline-oriented: for report-related questions it returns
    the latest generated report from the two-agent pipeline output stored in DB.
    """
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

        lowered = message.lower()
        report_query = any(
            token in lowered
            for token in [
                "отчет",
                "отч",
                "инцидент",
                "угроз",
                "severity",
                "критич",
                "послед",
                "лог",
            ]
        )

        if report_query:
            latest_report = await conn.fetchrow(
                """
                SELECT r.report_id, r.description, r.created_at
                FROM public."Reports" r
                ORDER BY r.created_at DESC
                LIMIT 1
                """
            )
            if latest_report:
                response = (
                    f"Последний отчет #{latest_report['report_id']} "
                    f"({latest_report['created_at'].isoformat()}):\n\n"
                    f"{latest_report['description']}"
                )
                mode = "report_context"
            else:
                response = (
                    "Пока нет сформированных отчетов. "
                    "Загрузите лог в чат или отправьте внешние логи в pipeline."
                )
                mode = "no_reports"
        else:
            response = (
                "Работаю через v2 pipeline (Agent1 -> RAG -> Agent2). "
                "Спросите про последний отчет, уровень угрозы или рекомендации."
            )
            mode = "assistant"

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
