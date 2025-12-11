# log_analysis_service.py
# Сервис для анализа логов с интеграцией GigaChat

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from log_ai_agent.config.cfg import GIGACHAT_API_KEY
from log_ai_agent.default_logs_analyse.log_analyzer import LogAnalyzer

logger = logging.getLogger(__name__)


async def get_threat_types(conn: asyncpg.Connection) -> list[dict]:
    """Получить все типы угроз из БД."""
    rows = await conn.fetch("""
        SELECT threat_type_id, name
        FROM public."ThreatTypes"
        ORDER BY threat_type_id
    """)

    return [{"id": row["threat_type_id"], "name": row["name"]} for row in rows]


async def get_severity_levels(conn: asyncpg.Connection) -> list[dict]:
    """Получить все уровни серьезности из БД."""
    rows = await conn.fetch("""
        SELECT severity_level_id, name
        FROM public."SeverityLevels"
        ORDER BY severity_level_id
    """)

    return [{"id": row["severity_level_id"], "name": row["name"]} for row in rows]


async def save_log_to_db(
    conn: asyncpg.Connection, file_content: str, filename: str
) -> int:
    """Сохранить лог в БД.

    Args:
        conn: Подключение к БД
        file_content: Содержимое лог-файла
        filename: Имя файла (используется только для логирования)

    Returns:
        ID созданной записи лога

    """
    row = await conn.fetchrow(
        """
        INSERT INTO public."Logs" (file_content, date)
        VALUES ($1, NOW())
        RETURNING log_id
        """,
        file_content,
    )

    log_id = row["log_id"]
    logger.info(f"Лог сохранен в БД с ID: {log_id}, файл: {filename}")

    return log_id


async def create_report_from_analysis(
    conn: asyncpg.Connection,
    log_id: int,
    analysis_result: dict,
    threat_types: list[dict],
    severity_levels: list[dict],
    gigachat_response: str,
) -> int:
    """Создать отчет на основе анализа логов и ответа GigaChat.

    Args:
        conn: Подключение к БД
        log_id: ID лога
        analysis_result: Результат анализа от log_analyzer
        threat_types: Список типов угроз
        severity_levels: Список уровней серьезности
        gigachat_response: Ответ от GigaChat с анализом

    Returns:
        ID созданного отчета

    """
    # Парсим ответ GigaChat для извлечения severity_level_id и threat_type_id из метаданных

    description = gigachat_response
    severity_level_id = 3  # По умолчанию Средний
    threat_type_id = 11  # По умолчанию Другое

    # Извлекаем метаданные из конца ответа
    if "---META---" in gigachat_response:
        try:
            meta_start_idx = gigachat_response.index("---META---")
            # Убираем все, что после ---META--- (включая сам ---META---)
            description = gigachat_response[:meta_start_idx].strip()

            # Парсим метаданные
            meta_section = gigachat_response[meta_start_idx:]
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
    else:
        logger.warning(
            "Метаданные не найдены в ответе GigaChat, используем значения по умолчанию"
        )

    # Создаем отчет
    row = await conn.fetchrow(
        """
        INSERT INTO public."Reports" (
            log_id, 
            severity_level_id, 
            threat_type_id, 
            description, 
            created_at
        )
        VALUES ($1, $2, $3, $4, NOW())
        RETURNING report_id
        """,
        log_id,
        severity_level_id,
        threat_type_id,
        description,
    )

    report_id = row["report_id"]
    logger.info(
        f"Отчет создан: ID={report_id}, log_id={log_id}, "
        f"severity={severity_level_id}, threat={threat_type_id}"
    )

    return report_id


async def analyze_log_with_gigachat(
    log_content: str,
    analysis_result: dict,
    threat_types: list[dict],
    severity_levels: list[dict],
) -> str:
    """Отправить результаты анализа логов в GigaChat для создания отчета.

    Args:
        log_content: Содержимое лог-файла
        analysis_result: Результат классического анализа
        threat_types: Список типов угроз
        severity_levels: Список уровней серьезности

    Returns:
        Ответ от GigaChat в формате JSON

    """
    # Формируем промпт для GigaChat
    prompt = f"""Ты - эксперт по кибербезопасности. Проанализируй лог-файл и создай детальный отчет о безопасности.

СОДЕРЖИМОЕ ЛОГ-ФАЙЛА:
```
{log_content[:5000]}
```
{"... (показана часть лог-файла)" if len(log_content) > 5000 else ""}

ТВОЯ ЗАДАЧА:
1. Проанализируй содержимое лог-файла
2. Обрати внимание на:
   - Ошибки и исключения
   - Подозрительные паттерны активности
   - Попытки несанкционированного доступа
   - Аномалии в поведении системы
   - Критические события
3. Создай ПОДРОБНЫЙ отчет с конкретными примерами из лога

ВАЖНО:
- Приводи КОНКРЕТНЫЕ строки из лога
- Давай ПРАКТИЧЕСКИЕ рекомендации по устранению
- Если проблем не найдено, укажи это и опиши общее состояние системы
- НЕ упоминай никакие ID из базы данных, номера записей и техническую информацию
- НЕ пиши про типы угроз и уровни серьезности в тексте
- Пиши только конкретный отчет об обнаруженных проблемах или их отсутствии

ФОРМАТ ОТВЕТА:
Напиши ПОДРОБНЫЙ анализ в формате markdown:
- Используй заголовки, списки, выделение жирным
- Приводи конкретные строки из лога в блоках кода
- Давай практические рекомендации
- Пиши как эксперт по безопасности, общаясь с пользователем

В САМОМ КОНЦЕ ответа (после всего текста) добавь служебную информацию в формате:
---META---
severity_level_id: <число от 1 до 4: 1-Критический, 2-Высокий, 3-Средний, 4-Низкий>
threat_type_id: <число от 1 до 11: 1-Вторжение, 2-Вредоносное ПО, 3-DDoS, 4-Утечка данных, 5-Несанкционированный доступ, 6-Фишинг, 7-SQL-инъекция, 8-XSS, 9-Брутфорс, 10-Сканирование портов, 11-Другое>
---END---

ПОМНИ: Блок ---META--- должен быть ПОЛНОСТЬЮ СКРЫТ от пользователя и использоваться только системой!"""

    try:
        with GigaChat(
            credentials=GIGACHAT_API_KEY,
            scope="GIGACHAT_API_PERS",
            verify_ssl_certs=False,
        ) as giga:
            messages = [Messages(role=MessagesRole.USER, content=prompt)]
            chat = Chat(messages=messages, max_tokens=2000, temperature=0.3)

            response_model = giga.chat(chat)
            response = response_model.choices[0].message.content

            # Убираем возможные обёртки markdown
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Убираем блок META из ответа перед возвратом
            if "---META---" in response:
                meta_start_idx = response.index("---META---")
                response = response[:meta_start_idx].strip()

            logger.info(f"GigaChat response for log analysis: {response[:200]}...")

            return response

    except Exception as e:
        logger.error(f"Ошибка при обращении к GigaChat: {e}")
        # Возвращаем текстовый ответ с метаданными в случае ошибки
        return f"""## Ошибка анализа

К сожалению, произошла ошибка при анализе лог-файла: {str(e)}

Пожалуйста, попробуйте загрузить файл снова или обратитесь к администратору системы.

---META---
severity_level_id: 3
threat_type_id: 11
---END---"""


async def process_log_file(
    user_id: int, filename: str, file_content: str, database_url: str
) -> dict[str, Any]:
    """Полный цикл обработки лог-файла:
    1. Классический анализ
    2. Сохранение в БД (таблица Logs)
    3. Анализ через GigaChat
    4. Создание отчета (таблица Reports)

    Args:
        user_id: ID пользователя
        filename: Имя файла
        file_content: Содержимое файла
        database_url: URL БД

    Returns:
        Результат обработки

    """
    conn = await asyncpg.connect(database_url, timeout=10)

    try:
        # Шаг 1: Классический анализ логов
        logger.info(f"Начало анализа файла {filename} для пользователя {user_id}")

        # Сохраняем временный файл для анализатора
        temp_path = Path(f"/tmp/{filename}")
        temp_path.write_text(file_content, encoding="utf-8")

        analyzer = LogAnalyzer()
        incidents = analyzer.analyze_log_file(temp_path)

        analysis_result = {
            "success": True,
            "filename": filename,
            "total_incidents": len(incidents),
            "incidents": incidents,
            "analyzed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"Классический анализ завершен: найдено {len(incidents)} инцидентов"
        )

        # Шаг 2: Подготавливаем содержимое для сохранения в БД
        # Извлекаем context из всех инцидентов
        if incidents and len(incidents) > 0:
            contexts = []
            for incident in incidents:
                if "context" in incident and incident["context"]:
                    contexts.append(incident["context"])

            if contexts:
                log_content_to_save = "\n\n".join(contexts)
            else:
                log_content_to_save = "Нет инцидентов"
        else:
            log_content_to_save = "Нет инцидентов"

        log_id = await save_log_to_db(conn, log_content_to_save, filename)

        # Шаг 3: Получаем справочники из БД
        threat_types = await get_threat_types(conn)
        severity_levels = await get_severity_levels(conn)

        logger.info(
            f"Загружено {len(threat_types)} типов угроз и {len(severity_levels)} уровней серьезности"
        )

        # Шаг 4: Анализ через GigaChat
        gigachat_response = await analyze_log_with_gigachat(
            file_content, analysis_result, threat_types, severity_levels
        )

        # Шаг 5: Создаем отчет
        report_id = await create_report_from_analysis(
            conn,
            log_id,
            analysis_result,
            threat_types,
            severity_levels,
            gigachat_response,
        )

        # Удаляем временный файл
        temp_path.unlink(missing_ok=True)

        return {
            "success": True,
            "log_id": log_id,
            "report_id": report_id,
            "analysis": analysis_result,
            "gigachat_analysis": gigachat_response,
            "message": f"Файл {filename} успешно проанализирован. Найдено {len(incidents)} инцидентов.",
        }

    except Exception as e:
        logger.error(f"Ошибка при обработке файла {filename}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Ошибка при обработке файла {filename}",
        }

    finally:
        await conn.close()
