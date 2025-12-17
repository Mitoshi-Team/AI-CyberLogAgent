# gigachat_async.py
# Асинхронная версия для интеграции с FastAPI

import logging
import asyncio

import asyncpg

from .RAG_gigachat import ask_gigachat

logger = logging.getLogger(__name__)


async def get_last_messages(
    conn: asyncpg.Connection, user_id: int, limit: int = 20
) -> list[dict]:
    """Получить последние N сообщений пользователя из базы данных."""
    rows = await conn.fetch(
        """
        SELECT role, content, created_at 
        FROM public."Messages" 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT $2
        """,
        user_id,
        limit,
    )

    # Возвращаем в обратном порядке (от старых к новым)
    return [
        {
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
        }
        for row in reversed(rows)
    ]


async def process_chat_message(
    user_id: int, user_message: str, database_url: str
) -> str:
    """Обработать сообщение пользователя с помощью GigaChat.

    Args:
        user_id: ID пользователя
        user_message: Сообщение от пользователя
        database_url: URL подключения к базе данных

    Returns:
        Ответ от GigaChat

    """
    conn = await asyncpg.connect(database_url, timeout=5)

    try:
        # Сохраняем сообщение пользователя
        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "user",
            user_message,
        )

        # Получаем последние 20 сообщений для контекста
        history = await get_last_messages(conn, user_id, limit=20)

        logger.info(
            f"GigaChat context: загружено {len(history)} сообщений для пользователя {user_id}"
        )

        # Для RAG-версии вызываем обёртку ask_gigachat в отдельном потоке
        # Ограничиваем время выполнения, чтобы не блокировать обработчик
        try:
            last_msgs = history[-10:]
            history_lines = [f"{m['role']}: {m['content']}" for m in last_msgs]
            history_text = "\n".join(history_lines)
            formatted_question = (
                f"История диалога:\n{history_text}\nВопрос: {user_message}"
                if history_text
                else f"Вопрос: {user_message}"
            )

            # Запускаем синхронную RAG-функцию в пуле потоков с таймаутом
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(ask_gigachat, formatted_question), timeout=30
                )
            except asyncio.TimeoutError:
                logger.error(f"ask_gigachat timed out for user {user_id}")
                response = "Извините, запрос занял слишком много времени. Попробуйте позже."
            except Exception as e:
                logger.error(f"Error in ask_gigachat for user {user_id}: {e}")
                response = f"Извините, произошла ошибка при обращении к GigaChat: {str(e)}"
        except Exception as e:
            response = f"Извините, произошла ошибка при формировании контекста: {str(e)}"

        # Сохраняем ответ агента в базу данных
        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "agent",
            response,
        )

        logger.info(f"GigaChat: ответ сохранен для пользователя {user_id}")

        return response

    finally:
        await conn.close()


async def clear_user_context(user_id: int, database_url: str) -> int:
    """Очистить весь контекст (историю сообщений) для пользователя.

    Args:
        user_id: ID пользователя
        database_url: URL подключения к базе данных

    Returns:
        Количество удаленных сообщений

    """
    conn = await asyncpg.connect(database_url, timeout=5)

    try:
        # Удаляем все сообщения пользователя
        result = await conn.execute(
            """
            DELETE FROM public."Messages"
            WHERE user_id = $1
            """,
            user_id,
        )

        # Извлекаем количество удаленных записей
        deleted_count = int(result.split()[-1])

        logger.info(
            f"GigaChat context: очищено {deleted_count} сообщений для пользователя {user_id}"
        )

        return deleted_count

    finally:
        await conn.close()
