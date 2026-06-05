# AI Agent v2 — Модуль анализа логов с RAG

## Описание

**AI Agent v2** — модуль интеллектуального анализа логов безопасности с использованием RAG (Retrieval-Augmented Generation), базы знаний MITRE ATT&CK и сигнатурных движков YARA/Sigma.

### Особенности

- **Четырёхэтапная аналитика с LangGraph**:
  - **Agent 1**: Первичный анализ логов, выявление событий безопасности с timestamps
  - **Description Agent**: Генерация структурированных описаний для каждой группы событий
  - **Agent 2**: RAG-поиск MITRE-техник по описаниям от Description Agent (параллельно)
  - **Agent 3**: Финальный отчёт с объединением Agent 1 (напрямую), Description Agent → Agent 2, YARA и Sigma

- **Сигнатурные движки**:
  - **YARA** (`yara-python`) — обнаружение малвари, эксплойтов, паттернов атак
  - **Sigma** (`pysigma`) — SIEM-детекции для Apache логов

- **Гибкая LLM-архитектура**:
  - **Ollama (on-premise)** — полная локальная работа, данные не покидают периметр
  - Автоматическое определение провайдера по переменным окружения

- **RAG (Retrieval-Augmented Generation)**:
  - Векторный поиск по техникам MITRE ATT&CK (ChromaDB)
  - **Новый подход**: отдельный RAG-запрос для каждого события (не один запрос на все логи)
  - Параллельный RAG с семафором для ограничения concurrency

---

## Архитектура пайплайна

```
┌──────────────────────────────────────────────────────────────┐
│                     log_content (input)                      │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Prefilter  │   │parse_logs   │   │  YARA Scan  │
└──────┬──────┘   │  (Apache    │   │  (parallel) │
       │          │   parser)   │   └──────┬──────┘
       ▼          └──────┬──────┘          │
┌─────────────┐          │                  ▼
│   Agent 1   │          │           ┌─────────────┐
│  (primary   │          │           │ Sigma Scan  │
│   analysis) │          │           │  (parallel) │
└──┬───┬──────┘          │           └──────┬──────┘
   │   │                 │                   │
   │   │                 └────────┬──────────┘
   │   └──────────────────┐      │
   │                      │      │
┌──▼───────────┐   ┌──────▼──────▼─────┐
│ Description  │   │                  │
│   Agent      │   │    Agent 3       │
│ (generates   │   │  (summarize)     │
│ descriptions)│   │                  │
└──┬───────────┘   └────────┬─────────┘
   │                        │
┌──▼───────────┐            │
│ Agent 2 (RAG)│───────────▶│
│  (parallel)  │            │
└──────────────┘            ▼
                     ┌─────────────┐
                     │ END (report)│
                     └─────────────┘
```

### Поток данных

1. **Prefilter** → фильтрация "мусорных" строк (heartbeat, health check)
2. **Agent 1** → первичный анализ, возвращает `groups` (список групп событий с описанием, timestamp, log_line)
   — параллельно уходит **напрямую в Agent 3** и в **Description Agent**
3. **Description Agent** → для каждой группы генерирует структурированное описание: категория угрозы, ключевые слова (RU/EN), severity, временной диапазон
4. **YARA/Sigma** → сканируют параллельно после `parse_logs`
5. **Agent 2 (RAG)** → для каждого описания от Description Agent делает RAG-запрос, накапливает `mitre_techniques_final`
6. **Agent 3** → получает всё: Agent 1 (напрямую), MITRE-техники от Agent 2, YARA/Sigma совпадения, генерирует финальный отчёт

### MITRE техники с timestamp

Каждая техника содержит привязку к времени из оригинального лога:

```python
{
    "technique_id": "T1110",
    "name": "Brute Force",
    "timestamp": "2025-12-17 13:06:10",  # из лога
    "event": "Brute force attack on admin account",
    "log_line": "[Wed Dec 17 13:06:10 2025] [error] ...Possible brute force attack..."
}
```

---

## Структура модуля

```
ai_agent_v2/
├── chains/                     # LLM-цепочки для агентов
│   ├── agent1.py              # Первичный анализ логов
│   ├── agent2.py              # RAG-обогащение событий
│   ├── agent3.py              # Финальная суммаризация
│   ├── description_agent.py   # Генерация описаний техник
│   ├── graph_nodes.py        # LangGraph узлы
│   ├── llm.py                # LLM провайдер
│   ├── prefilter.py          # Предобработка логов
│   ├── rag_chain.py          # RAG-поиск MITRE
│   ├── yara_generator.py     # Генерация YARA-правил
│   ├── __init__.py
│   └── providers/            # LLM провайдеры
│       ├── base.py           # Базовый класс
│       ├── ollama.py         # Ollama провайдер
│       ├── openai.py         # OpenAI-совместимый провайдер
│       └── __init__.py
├── engines/                    # Сигнатурные движки
│   ├── yara_engine.py         # YARA на yara-python
│   ├── sigma_engine.py        # Sigma на pysigma
│   └── __init__.py
├── models/                     # Типы данных
│   ├── schemas.py             # Pydantic схемы
│   └── __init__.py
├── parsers/                    # Парсеры логов
│   └── apache_parser.py       # Apache парсер
├── rules/                      # Правила обнаружения
│   ├── yara/
│   │   ├── SQL_Injection_Advanced.yar
│   │   ├── XSS_Advanced.yar
│   │   ├── Path_Traversal_Advanced.yar
│   │   ├── Sensitive_File_Access.yar
│   │   ├── RCE_Payloads.yar
│   │   ├── WebShell_Indicators.yar
│   │   ├── Security_Scanner_Signatures.yar
│   │   └── Protocol_Anomalies.yar
│   └── sigma/
│       ├── brute_force_authentication.yml
│       ├── mimikatz_detection.yml
│       ├── path_traversal.yml
│       ├── powershell_encoded_command.yml
│       ├── remote_file_inclusion.yml
│       ├── reverse_shell_detection.yml
│       ├── scanner_detection.yml
│       ├── sql_injection_attempt.yml
│       └── xss_attempt.yml
├── pipeline/                    # LangGraph pipeline
│   ├── langgraph_pipeline.py   # LangGraph StateGraph
│   ├── README_PIPELINE.md      # Документация пайплайна
│   └── __init__.py
├── knowledge_base/             # База знаний MITRE ATT&CK
│   ├── manager.py              # ChromaDB менеджер
│   ├── mitre_loader.py         # Загрузчик MITRE (из mitre_processed.json)
│   ├── mitre_processed.json    # Обработанные техники MITRE (основной источник)
│   ├── enterprise-attack.json  # STIX-дамп (резервный)
│   └── __init__.py
├── embedding/                  # Эмбеддинги
│   ├── manager.py              # Менеджер эмбеддингов
│   ├── models/                 # Скачанная модель (не в Git)
│   │   └── multilingual-e5-base/
│   └── __init__.py
├── prompts/                    # Промты для агентов
│   ├── system.py
│   ├── log_analysis.py
│   ├── yara_generation.py
│   └── __init__.py
├── visual_graph/               # Визуализация графа
│   ├── render_graph.py         # Рендер графа
│   └── pipeline_graph.mmd      # Mermaid диаграмма
├── metrics/                    # Метрики качества детекции
│   ├── evaluate.py             # Сравнение ground truth с детекциями
│   ├── metrics_logger.py       # Логирование метрик после анализа
│   ├── README_METRICS.md       # Документация метрик
│   ├── pipeline_metrics.log    # Журнал детекций (создаётся автоматически)
│   └── TESTS_DATA/
│       ├── SUMMARY_REPORT.md   # Сводка метрик
│       ├── test1/              # Сырые данные теста 1
│       └── test2/              # Отчёт и верификация теста 2
├── pipeline_tests/             # Тесты
│   ├── conftest.py
│   ├── rag_ground_truth.json
│   ├── run_rag_eval.py
│   ├── test_agent1.py
│   ├── test_agent3.py
│   ├── test_description_agent.py
│   ├── test_full_pipeline.py
│   ├── test_graph_nodes.py
│   ├── test_llm.py
│   ├── test_new_features.py
│   ├── test_pipeline_basic.py
│   ├── test_prefilter.py
│   ├── test_quick.py
│   ├── test_rag.py
│   ├── test_rag_eval.py
│   ├── test_rag_evaluation.py
│   ├── test_rag_flow.py
│   ├── test_yara.py
│   ├── test_yara_generator.py
│   ├── test_yara_sigma.py
│   └── __init__.py
├── examples/                   # Примеры использования
│   ├── basic.py
│   └── __init__.py
├── chroma_db/                  # Векторная база (генерируется, не в Git)
├── app_integration.py          # Интеграция с FastAPI
├── callbacks.py                # Колбэки
├── chat_integration.py         # Интеграция чата
├── config.py                   # Конфигурация агента
├── init_mitre.py               # Инициализация MITRE
├── models_types.py             # Типы моделей
├── run.py                      # Точка входа
├── __init__.py
└── README.md
```

---

## Установка

### 1. Клонирование репозитория

```bash
git clone https://gitverse.ru/mitoshi_team/AI-CyberLogAgent
cd AI-CyberLogAgent
```

### 2. Установка зависимостей

Проект использует `uv` для управления зависимостями:

```bash
# Установить uv (если не установлен)
pip install uv

# Синхронизировать зависимости
uv sync

# Или установить вручную
uv pip install pytest pytest-asyncio langchain-core langchain-community langgraph yara-python pysigma chromadb langchain-chroma
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корневой папке проекта:

```bash
# === LLM провайдер ===

# Вариант 1: Ollama (on-premise / локальный сервер) — РЕКОМЕНДУЕТСЯ
# Ollama должен быть запущен на указанном URL
# Важно: установите модель через `ollama pull <model>`
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=TinyLlama:1.1b  # или qwen2.5:7b, llama3.1:8b

# Общие настройки LLM
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4000
LLM_TIMEOUT=90
```

> **Важно**: Перед использованием Ollama убедитесь, что модель установлена:
> ```bash
> ollama pull TinyLlama:1.1b
> # или
> ollama pull qwen2.5:7b
> ```

---

## Быстрый старт

### Запуск тестов

```bash
# YARA/Sigma + pipeline nodes (быстрый, без LLM)
uv run python -m pytest log_ai_agent/ai_agent_v2/pipeline_tests/test_yara_sigma.py -v

# Полный пайплайн (с LLM, требует Ollama)
uv run python log_ai_agent/ai_agent_v2/pipeline_tests/test_full_pipeline.py
```

### Запуск через pytest

```bash
# Все тесты
uv run python -m pytest log_ai_agent/ai_agent_v2/pipeline_tests/ -v

# С подробным выводом
uv run python -m pytest log_ai_agent/ai_agent_v2/pipeline_tests/test_yara_sigma.py -vv -s -rA
```

---

## Использование в коде

### Базовый пример

```python
import asyncio
from log_ai_agent.ai_agent_v2 import create_pipeline


async def analyze_logs():
    # Создание пайплайна
    pipeline = await create_pipeline(
        use_rag=True,
        yara_rules_path="log_ai_agent/ai_agent_v2/rules/yara",
        sigma_rules_path="log_ai_agent/ai_agent_v2/rules/sigma",
    )

    # Логи для анализа (Apache syslog формат)
    log_content = """
[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed for user admin from 192.168.1.100
[Wed Dec 17 13:06:10 2025] [error] [client 89.23.74.19] Possible brute force attack from 89.23.74.19
[Wed Dec 17 13:06:20 2025] [error] [client 45.17.158.24] SQL injection attempt: OR 1=1 DROP TABLE users
    """

    # Анализ
    result = await pipeline.analyze(log_content=log_content)

    if result.get("success"):
        stages = result.get("stages", {})

        # Agent 1: события с timestamps
        agent1 = stages.get("agent1", {})
        print(f"Событий: {agent1.get('events_found')}")

        # Agent 2: MITRE техники
        agent2 = stages.get("agent2", {})
        techniques = agent2.get("mitre_techniques", [])
        for t in techniques:
            print(f"  {t['technique_id']} @ {t['timestamp']}: {t['name']}")

        # YARA совпадения
        yara = stages.get("yara", {})
        print(f"YARA: {yara.get('yara_rules_matched', [])}")

        # Sigma совпадения
        sigma = stages.get("sigma", {})
        print(f"Sigma: {sigma.get('sigma_rules_matched', [])}")

        # Agent 3: финальный отчёт
        agent3 = stages.get("agent3", {})
        print(f"Severity: {agent3.get('severity_level_id')}/4")
        print(f"Report: {agent3.get('final_report', '')[:500]}")


if __name__ == "__main__":
    asyncio.run(analyze_logs())
```

### Создание пайплайна

```python
from log_ai_agent.ai_agent_v2 import create_pipeline

# Полный пайплайн (RAG + YARA + Sigma)
pipeline = await create_pipeline(
    use_rag=True,
    yara_rules_path="path/to/yara/rules",
    sigma_rules_path="path/to/sigma/rules",
)

# Без RAG (только Agent 1 + YARA/Sigma)
pipeline = await create_pipeline(use_rag=False)

# Без YARA/Sigma
pipeline = await create_pipeline(use_rag=True)
```

---

## YARA и Sigma движки

### YARA Engine

Использует `yara-python` для обнаружения паттернов атак:

```python
from log_ai_agent.ai_agent_v2.engines import YaraEngine

engine = YaraEngine("path/to/rules.yar")
matches = engine.scan(parsed_logs)
```

**Поддерживаемые паттерны:**
- Brute Force индикаторы
- SQL Injection
- XSS попытки
- Directory traversal
- Command injection

### Sigma Engine

Использует `pysigma` для SIEM-детекций:

```python
from log_ai_agent.ai_agent_v2.engines import SigmaEngine

engine = SigmaEngine("path/to/sigma/rules")
matches = engine.scan(parsed_logs)
```

**Правила Sigma:**
- XSS Attempt Detection
- SQL Injection Detection
- Brute Force Detection
- Command Injection Detection

### Apache Log Parser

Универсальный парсер для форматов:
- **Syslog**: `[Wed Dec 17 13:06:06 2025] [error] [client IP] message`
- **CLF**: `IP - - [timestamp] "request" status`
- **Combined**: CLF + referer + user-agent

```python
from log_ai_agent.ai_agent_v2.parsers import ApacheLogParser

parser = ApacheLogParser()
parsed = parser.parse(log_content)
# [{'raw': '...', 'timestamp': datetime(...), 'level': 'error', 'client_ip': '...', ...}]
```

---

## Тестирование

### Запуск тестов

```bash
# YARA/Sigma тесты (быстрые, ~1 сек)
uv run python -m pytest log_ai_agent/ai_agent_v2/pipeline_tests/test_yara_sigma.py -v

# Полный пайплайн (с LLM)
uv run python log_ai_agent/ai_agent_v2/pipeline_tests/test_full_pipeline.py

# Подробный вывод
uv run python -m pytest log_ai_agent/ai_agent_v2/pipeline_tests/ -vv -s -rA
```

### Проверка MITRE базы

```bash
# Загрузка MITRE в ChromaDB
rm -rf log_ai_agent/ai_agent_v2/chroma_db
# Запустить пайплайн (автоматически скачает и загрузит MITRE)

# Проверка количества техник
uv run python -c "
import chromadb
client = chromadb.PersistentClient(path='log_ai_agent/ai_agent_v2/chroma_db')
coll = client.get_collection('mitre_collection')
print(f'Техник в базе: {coll.count()}')
"
```

---

## MITRE ATT&CK

### Источник данных

- **Файл**: `knowledge_base/mitre_processed.json` — проектный файл с обработанными техниками (88 шт.)
- **Формат**: JSON (id, name, description, tactic)
- **Источник**: обработанный MITRE ATT&CK — только основные техники, без GitHub/STIX загрузки

### Обновление базы

```bash
# Удалить существующую базу
rm -rf log_ai_agent/ai_agent_v2/chroma_db

# Переинициализировать (загрузится из mitre_processed.json)
uv run python log_ai_agent/ai_agent_v2/init_mitre.py
```

---

## Конфигурация

### LLM провайдеры

**Ollama (on-premise)**

```bash
# .env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=TinyLlama:1.1b
```

**Использование в коде:**

```python
from log_ai_agent.ai_agent_v2 import create_llm, LLMProvider

# Автоматический выбор провайдера (по .env)
llm = create_llm()

# Принудительное указание провайдера
llm = create_llm(provider=LLMProvider.OLLAMA)
```

### Параметры RAG

```python
pipeline = await create_pipeline(
    use_rag=True,
    rag_top_k=5,  # Количество MITRE техник на событие
)
```

---

## Устранение неполадок

### "model 'qwen2.5:7b' not found"

**Причина**: Модель не установлена в Ollama.

**Решение**:
```bash
ollama pull TinyLlama:1.1b
# или
ollama pull qwen2.5:7b
```

### "No LLM provider configured"

**Причина**: Не настроены переменные окружения.

**Решение**: Добавить в `.env`:
```bash
OLLAMA_URL=http://localhost:11434
```

### "ChromaDB not initialized"

**Причина**: База данных не инициализирована.

**Решение**:
```bash
rm -rf log_ai_agent/ai_agent_v2/chroma_db
# MITRE загрузится автоматически при запуске приложения
```

---

## Лицензия

MITRE ATT&CK лицензируется в соответствии с [Terms of Use](https://attack.mitre.org/resources/terms-of-use/).

Данный модуль использует MITRE ATT&CK для образовательных и исследовательских целей.
