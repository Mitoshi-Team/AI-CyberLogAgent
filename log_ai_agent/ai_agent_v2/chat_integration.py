import json
import logging

from sqlalchemy import select, delete, func
from log_ai_agent.db.session import get_async_session
from log_ai_agent.db.models import Message, Report
from langchain_core.messages import HumanMessage, SystemMessage

from .chains.llm import create_llm

logger = logging.getLogger(__name__)


CHAT_SYSTEM_PROMPT = """Ты - AI-ассистент по кибербезопасности в системе Wavescan.
Отвечай на русском языке, по существу и с практическими рекомендациями.

Правила ответа:
- Используй контекст диалога и данные последнего отчета, если они доступны.
- Если пользователь задает вопрос, на который нет данных в контексте, честно скажи, что не знаешь, и предложи следующий шаг (например, запросить больше информации).
- Если пользователь ни слова не говорит о последнем отчете, не упоминай его в ответе.
- Если данных для точного вывода недостаточно, явно укажи это и предложи следующий шаг.
- Не выдумывай факты, которых нет в переданных данных.
- Формулируй ответ как нормальный диалоговый ответ ассистента, без служебных меток.
"""


SUGGESTION_PROMPT = """На основе последнего диалога и ответа ассистента придумай 3 короткие подсказки (максимум 2 слова каждая, на русском языке), которые помогут пользователю продолжить общение.

Подсказки должны:
- Быть релевантны контексту разговора
- Быть полезными и практичными
- Состоять максимум из 2 слов
- Быть на русском языке

Верни ТОЛЬКО 3 подсказки, по одной на строке, без нумерации и без пояснений."""


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
    session,
    user_id: int,
    user_message: str,
) -> dict:
    """Generate chat response and suggestions via LLM."""
    stmt = (
        select(Message)
        .where(Message.user_id == user_id, Message.role.in_(["user", "agent"]))
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    res = await session.execute(stmt)
    history_rows = res.scalars().all()

    latest_stmt = select(Report).order_by(Report.created_at.desc()).limit(1)
    latest_res = await session.execute(latest_stmt)
    latest_report = latest_res.scalars().first()

    history_lines: list[str] = []
    for msg in reversed(history_rows):
        role = "Пользователь" if msg.role == "user" else "Агент"
        history_lines.append(f"[{msg.created_at.isoformat()}] {role}: {msg.content}")

    history_text = "\n".join(history_lines) if history_lines else "История отсутствует"

    if latest_report:
        report_context = (
            f"ID: {latest_report.report_id}\n"
            f"Время: {latest_report.created_at.isoformat()}\n"
            f"Описание:\n{latest_report.description}"
        )
    else:
        report_context = "Отчеты пока отсутствуют"

    llm = create_llm()
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

    # Generate suggestions based on the conversation context
    suggestions = await generate_suggestions(
        session=session, user_id=user_id, user_message=user_message,
        agent_response=response, history_text=history_text,
        report_context=report_context
    )

    return {"response": response, "suggestions": suggestions}


async def generate_suggestions(
    session,
    user_id: int,
    user_message: str,
    agent_response: str,
    history_text: str,
    report_context: str,
) -> list[str]:
    """Generate 3 short suggestions (max 2 words each) based on conversation context."""
    try:
        llm = create_llm()
        suggestion_result = await llm.ainvoke(
            [
                SystemMessage(content=SUGGESTION_PROMPT),
                HumanMessage(
                    content=(
                        "Контекст ответа ассистента:\n"
                        f"{agent_response}\n\n"
                        "История диалога:\n"
                        f"{history_text}\n\n"
                        "Текущее сообщение пользователя:\n"
                        f"{user_message}\n\n"
                        "Контекст последнего отчета:\n"
                        f"{report_context}"
                    )
                ),
            ]
        )

        raw_text = _extract_llm_text(suggestion_result)
        suggestions = [line.strip().lstrip("1234567890.-").strip() for line in raw_text.split("\n") if line.strip()]
        suggestions = [s for s in suggestions if len(s.split()) <= 2][:3]

        if not suggestions:
            suggestions = ["Рекомендации", "Тренды", "MITRE"]
        while len(suggestions) < 3:
            suggestions.append("Рекомендации")
        return suggestions[:3]
    except Exception as e:
        logger.warning(f"Failed to generate suggestions: {e}")
        return ["Рекомендации", "Тренды", "MITRE"]


async def clear_user_context(user_id: int, database_url: str) -> int:
    """Clear all chat messages for a user and return deleted row count."""
    async with get_async_session() as session:
        count_stmt = select(func.count()).where(Message.user_id == user_id)
        count_res = await session.execute(count_stmt)
        count = int(count_res.scalar() or 0)
        await session.execute(delete(Message).where(Message.user_id == user_id))
        await session.commit()
        return count


async def process_chat_message(
    user_id: int, user_message: str, database_url: str
) -> dict:
    """Process a user chat message and save the agent response.

    The frontend persists the user message immediately before calling this
    flow, so the backend only appends the generated assistant reply.
    """
    message = (user_message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty")

    async with get_async_session() as session:
        result = await _generate_agent_response(session=session, user_id=user_id, user_message=message)
        response = result["response"]
        suggestions = result["suggestions"]
        mode = "agent_llm"

        agent_msg = Message(user_id=user_id, role="agent", content=response, suggestions=json.dumps(suggestions, ensure_ascii=False))
        session.add(agent_msg)
        await session.commit()

        return {"response": response, "suggestions": suggestions, "mode": mode}
