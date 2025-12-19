# gigachat.py
# Единый модуль для работы с GigaChat: RAG, обычные запросы и анализ логов

import asyncio
import logging
import os

import asyncpg
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
from langchain.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_gigachat.chat_models import GigaChat as LangChainGigaChat
from langchain_huggingface import HuggingFaceEmbeddings

from log_ai_agent.config.cfg import GIGACHAT_API_KEY

logger = logging.getLogger(__name__)

# ============================================================================
# ОБЩИЙ СИСТЕМНЫЙ ПРОМПТ
# ============================================================================

SYSTEM_PROMPT = """Ты - эксперт по кибербезопасности и анализу инцидентов безопасности.
Твоя задача - помогать пользователям анализировать логи, выявлять угрозы и давать 
рекомендации по обеспечению безопасности на основе базы знаний MITRE ATT&CK.

При ответе:
- Будь конкретным и точным
- Ссылайся на тактики и техники MITRE ATT&CK когда это уместно
- Указывай какая линия защиты (1, 2, 3) отвечает за обработку угрозы
- Давай практические рекомендации
- Отвечай на русском языке кратко и по существу
- Если ты не знаешь ответа, просто скажи, что не знаешь
- Веди диалог естественно, отвечай на конкретные вопросы пользователя
"""

# Промпт для RAG с плейсхолдерами для контекста и вопроса
RAG_TEMPLATE = """Ты - эксперт по кибербезопасности. Используй предоставленные фрагменты базы знаний MITRE ATT&CK для ответа на вопрос.
Если информация есть в контексте, дай развернутый ответ и укажи какая линия защиты (1, 2, 3) занимается такими угрозами.
Если информации нет в контексте, дай общий ответ на основе своих знаний о кибербезопасности.
Отвечай естественно и по существу.

Контекст из базы знаний MITRE ATT&CK: {context}

Вопрос: {question}

Ответ на русском языке:"""

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ RAG (из RAG_gigachat.py)
# ============================================================================

LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")

# Инициализация локальных эмбеддингов и векторной базы
embeddings = None
vectorstore = None
use_vectorstore = False

try:
    embeddings = HuggingFaceEmbeddings(
        model_name=LOCAL_MODEL_DIR, model_kwargs={"local_files_only": True}
    )
    vectorstore = Chroma(
        persist_directory=os.path.join(os.path.dirname(__file__), "chroma_db"),
        embedding_function=embeddings,
        collection_name="mitre_collection",
    )
    use_vectorstore = True
    logger.info(f"Loaded local embeddings from {LOCAL_MODEL_DIR}")
except Exception as e:
    logger.warning(
        f"Local embeddings not available or failed to load from {LOCAL_MODEL_DIR}: {e}. "
        f"Falling back to LLM-only mode."
    )

# Инициализация LangChain GigaChat для RAG
llm = LangChainGigaChat(
    credentials=GIGACHAT_API_KEY,
    verify_ssl_certs=False,
    model="GigaChat",
    temperature=0.1,
)

# Используем RAG_TEMPLATE для RAG цепочки
QA_CHAIN_PROMPT = PromptTemplate.from_template(RAG_TEMPLATE)

# Создание RAG цепочки
if use_vectorstore and vectorstore is not None:
    rag_chain = (
        {
            "context": vectorstore.as_retriever(search_kwargs={"k": 5}),
            "question": RunnablePassthrough(),
        }
        | QA_CHAIN_PROMPT
        | llm
        | StrOutputParser()
    )
else:
    # Fallback: без векторной БД
    rag_chain = QA_CHAIN_PROMPT | llm | StrOutputParser()

# ============================================================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ============================================================================


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


# ============================================================================
# RAG ЗАПРОС
# ============================================================================


async def ask_gigachat_rag(question: str) -> str:
    """Отправить вопрос в GigaChat с использованием RAG (база знаний MITRE ATT&CK).

    Args:
        question: Вопрос от пользователя

    Returns:
        Ответ от GigaChat с контекстом из базы знаний

    """
    try:
        # Добавляем префикс для RAG
        formatted_question = f"query: {question}"

        # Запускаем синхронную RAG цепочку в отдельном потоке
        response = await asyncio.to_thread(rag_chain.invoke, formatted_question)

        logger.info(f"RAG response for question: {question[:100]}...")
        return response

    except Exception as e:
        logger.error(f"Ошибка при RAG запросе: {e}")
        return f"Извините, произошла ошибка при обращении к базе знаний: {str(e)}"


# ============================================================================
# ОБЫЧНЫЙ ТЕКСТОВЫЙ ЗАПРОС (без RAG)
# ============================================================================


async def ask_gigachat_text(user_message: str, history: list[dict] = None) -> str:
    """Обычный текстовый запрос к GigaChat без использования RAG.

    Args:
        user_message: Сообщение пользователя
        history: История диалога (опционально)

    Returns:
        Ответ от GigaChat

    """
    try:
        # Формируем сообщения
        messages = [Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT)]

        # Добавляем историю если есть
        if history:
            for msg in history[-10:]:  # Берем последние 10 сообщений
                role = (
                    MessagesRole.USER
                    if msg["role"] == "user"
                    else MessagesRole.ASSISTANT
                )
                messages.append(Messages(role=role, content=msg["content"]))

        # Добавляем текущее сообщение
        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        # Создаем чат и отправляем запрос в отдельном потоке
        def _sync_chat():
            with GigaChat(
                credentials=GIGACHAT_API_KEY,
                scope="GIGACHAT_API_PERS",
                verify_ssl_certs=False,
            ) as giga:
                chat = Chat(messages=messages, max_tokens=1000, temperature=0.3)
                response_model = giga.chat(chat)
                return response_model.choices[0].message.content

        response = await asyncio.to_thread(_sync_chat)

        logger.info(f"Text response for message: {user_message[:100]}...")
        return response

    except Exception as e:
        logger.error(f"Ошибка при текстовом запросе к GigaChat: {e}")
        return f"Извините, произошла ошибка при обращении к GigaChat: {str(e)}"


# ============================================================================
# АНАЛИЗ ЛОГА
# ============================================================================


async def analyze_log_with_gigachat(log_content: str) -> dict:
    """Отправить лог-файл на анализ в GigaChat с использованием RAG.

    Args:
        log_content: Содержимое лог-файла

    Returns:
        Словарь с результатом анализа:
        - description: текст отчета
        - severity_level_id: уровень серьезности (1-4)
        - threat_type_id: тип угрозы (1-11)

    """
    # Формируем вопрос для RAG с контекстом лог-файла
    log_preview = log_content[:5000]
    log_summary = f"Анализируется лог-файл ({len(log_content)} байт)"
    if len(log_content) > 5000:
        log_summary += " (показана часть)"

    question = f"""Проанализируй этот лог-файл на предмет инцидентов безопасности.

ЛОГ-ФАЙЛ:
```
{log_preview}
```
{log_summary}

ЗАДАЧА:
1. Выяви все подозрительные активности, ошибки и угрозы
2. Сопоставь обнаруженные паттерны с тактиками и техниками MITRE ATT&CK
3. Определи какая линия защиты (1, 2, 3) должна реагировать
4. Дай конкретные рекомендации по устранению

ФОРМАТ ОТВЕТА:
Создай ПОДРОБНЫЙ отчет в markdown с:
- Описанием обнаруженных угроз со ссылками на MITRE ATT&CK
- Конкретными строками из лога
- Практическими рекомендациями
- Указанием, какая линия защиты отвечает за обработку этих угроз

В КОНЦЕ добавь метаданные (определи, какой уровень серьезности и тип угрозы, не пиши тут заголовки и вообще ничего, кроме метаданных):
---META---
severity_level_id: <1-4: 1-Критический, 2-Высокий, 4-Низкий>
threat_type_id: <1-11: 1-Вторжение, 2-Malware, 3-DDoS, 4-Утечка, 5-Доступ, 6-Фишинг, 7-SQL, 8-XSS, 9-Брутфорс, 10-Сканирование, 11-Другое>
---END---
"""

    try:
        # Используем RAG для анализа с базой знаний MITRE ATT&CK
        response = await asyncio.wait_for(ask_gigachat_rag(question), timeout=60)

        logger.info(
            f"Log analysis with RAG completed, response length: {len(response)}"
        )

        # Парсим ответ
        description = response
        severity_level_id = 3  # По умолчанию Средний
        threat_type_id = 11  # По умолчанию Другое

        # Извлекаем метаданные
        if "---META---" in response:
            try:
                meta_start_idx = response.index("---META---")
                description = response[:meta_start_idx].strip()

                meta_section = response[meta_start_idx:]
                for line in meta_section.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        if key == "severity_level_id":
                            try:
                                severity_level_id = int(value)
                            except ValueError:
                                pass
                        elif key == "threat_type_id":
                            try:
                                threat_type_id = int(value)
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning(f"Не удалось извлечь метаданные из ответа GigaChat: {e}")

        logger.info(
            f"Log analysis completed, severity={severity_level_id}, threat={threat_type_id}"
        )

        return {
            "description": description,
            "severity_level_id": severity_level_id,
            "threat_type_id": threat_type_id,
        }

    except Exception as e:
        logger.error(f"Ошибка при анализе лога через GigaChat: {e}")
        return {
            "description": f"""## Ошибка анализа

К сожалению, произошла ошибка при анализе лог-файла: {str(e)}

Пожалуйста, попробуйте загрузить файл снова или обратитесь к администратору системы.""",
            "severity_level_id": 3,
            "threat_type_id": 11,
        }


# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ СООБЩЕНИЙ С СОХРАНЕНИЕМ В БД
# ============================================================================


def should_use_rag(message: str) -> bool:
    """Определить, нужно ли использовать RAG для данного вопроса.

    Анализирует сообщение на наличие ключевых слов, связанных с
    кибербезопасностью, MITRE ATT&CK и угрозами.

    Args:
        message: Сообщение пользователя

    Returns:
        True если нужно использовать RAG, False - для обычного диалога

    """
    # Ключевые слова, требующие базы знаний MITRE ATT&CK
    rag_keywords = [
        # MITRE ATT&CK
        "mitre",
        "att&ck",
        "attack",
        "тактика",
        "техника",
        "линия защиты",
        "линия",
        "защита",
        "матрица",
        # Типы угроз и атак
        "угроза",
        "атака",
        "вредонос",
        "malware",
        "эксплойт",
        "exploit",
        "уязвимость",
        "vulnerability",
        "вторжение",
        "intrusion",
        "компрометация",
        "compromise",
        "breach",
        # Тактики MITRE ATT&CK (на английском)
        "reconnaissance",
        "resource development",
        "initial access",
        "execution",
        "persistence",
        "privilege escalation",
        "defense evasion",
        "credential access",
        "discovery",
        "lateral movement",
        "collection",
        "command and control",
        "exfiltration",
        "impact",
        "c2",
        "c&c",
        # Тактики MITRE ATT&CK (на русском)
        "разведка",
        "эксплуатация",
        "закрепление",
        "повышение привилегий",
        "обход защиты",
        "кража учетных",
        "сбор данных",
        "утечка",
        # Конкретные угрозы
        "ddos",
        "dos",
        "injection",
        "инъекция",
        "sql",
        "xss",
        "csrf",
        "brute force",
        "брутфорс",
        "фишинг",
        "phishing",
        "ransomware",
        "троян",
        "trojan",
        "backdoor",
        "rootkit",
        "spyware",
        "keylogger",
        "botnet",
        "ботнет",
        # Действия злоумышленников
        "сканирование",
        "scanning",
        "enumeration",
        "перечисление",
        "escalation",
        "эскалация",
        "privilege",
        "привилегии",
    ]

    message_lower = message.lower()
    found = any(keyword in message_lower for keyword in rag_keywords)

    if found:
        logger.info(f"RAG mode auto-selected for message: {message[:50]}...")

    return found


async def process_chat_message(
    user_id: int, user_message: str, database_url: str, use_rag: bool = None
) -> dict:
    """Обработать сообщение пользователя с помощью GigaChat.

    Args:
        user_id: ID пользователя
        user_message: Сообщение от пользователя
        database_url: URL подключения к базе данных
        use_rag: Использовать ли RAG (база знаний MITRE ATT&CK).
                Если None - режим определяется автоматически по ключевым словам.
                True - принудительно RAG, False - обычный диалог.

    Returns:
        Словарь с ответом и информацией о режиме:
        - response: текст ответа
        - mode: режим работы ("RAG" или "TEXT")

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

        # Получаем последние сообщения для контекста
        history = await get_last_messages(conn, user_id, limit=20)

        # Автоматически определяем нужен ли RAG
        if use_rag is None:
            use_rag = should_use_rag(user_message)

        mode = "RAG" if use_rag else "TEXT"

        logger.info(
            f"Processing message for user {user_id}, mode: {mode}, history: {len(history)} messages"
        )

        # Выбираем режим работы
        try:
            if use_rag:
                # Формируем контекст с историей
                last_msgs = history[-10:]
                history_lines = [f"{m['role']}: {m['content']}" for m in last_msgs]
                history_text = "\n".join(history_lines)
                formatted_question = (
                    f"История диалога:\n{history_text}\nВопрос: {user_message}"
                    if history_text
                    else f"Вопрос: {user_message}"
                )

                # RAG запрос с таймаутом
                response = await asyncio.wait_for(
                    ask_gigachat_rag(formatted_question), timeout=30
                )
            else:
                # Обычный текстовый запрос с таймаутом
                response = await asyncio.wait_for(
                    ask_gigachat_text(user_message, history), timeout=30
                )

        except TimeoutError:
            logger.error(f"Request timed out for user {user_id}")
            response = "Извините, запрос занял слишком много времени. Попробуйте позже."
        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}")
            response = f"Извините, произошла ошибка при обработке запроса: {str(e)}"

        # Сохраняем ответ агента
        await conn.execute(
            """
            INSERT INTO public."Messages" (user_id, role, content, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            user_id,
            "agent",
            response,
        )

        logger.info(f"Response saved for user {user_id}, mode: {mode}")

        return {"response": response, "mode": mode}

    finally:
        await conn.close()
