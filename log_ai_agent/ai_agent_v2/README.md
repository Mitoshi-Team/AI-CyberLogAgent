# AI Agent v2 — Модуль анализа логов с RAG

## Описание

**AI Agent v2** — модуль интеллектуального анализа логов безопасности с использованием RAG (Retrieval-Augmented Generation) и базы знаний MITRE ATT&CK.

### Особенности

- **Двухэтапная аналитика**:
  - **Agent 1**: Первичный анализ логов, выявление событий безопасности
  - **Agent 2**: Финальный отчёт с использованием контекста MITRE ATT&CK

- **RAG (Retrieval-Augmented Generation)**:
  - Векторный поиск по техникам MITRE ATT&CK
  - ChromaDB для хранения эмбеддингов
  - Автоматическая загрузка актуальных данных с GitHub

- **Автоматическая инициализация**:
  - При первом запуске скачивает базу MITRE с GitHub
  - Сохраняет локально для офлайн-работы
  - Кэширует векторную базу для быстрого повторного использования

---

## Структура модуля

```
ai_agent_v2/
├── chains/                 # LLM-цепочки для агентов
│   ├── agent1.py          # Первичный анализ логов
│   ├── agent2.py          # Финальный отчёт
│   └── rag_chain.py       # RAG-поиск по MITRE
├── knowledge_base/         # База знаний MITRE ATT&CK
│   ├── manager.py         # ChromaDB менеджер
│   ├── mitre_loader.py    # Инициализация базы знаний
│   ├── local_loader.py    # Загрузка из локального JSON
│   └── github_loader.py   # Скачивание с GitHub
├── embedding/              # Эмбеддинги
│   └── manager.py         # Менеджер эмбеддингов
├── models/                 # Модели данных
│   └── models_types.py    # Типы угроз, severity
├── prompts/                # Промты для агентов
├── chroma_db/              # Векторная база (генерируется)
├── mitre_data/             # MITRE STIX JSON (генерируется)
├── test_rag_flow.py        # Тест полного цикла RAG
├── load_mitre_full.py      # Скрипт ручной загрузки MITRE
└── download_mitre.py       # Скрипт скачивания MITRE
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
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корневой папке проекта:

```bash
# GigaChat API (для LLM)
GIGACHAT_CLIENT_ID=your_client_id
GIGACHAT_CLIENT_SECRET=your_client_secret
GIGACHAT_AUTH_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v2

# База данных (если используется)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

---

## Быстрый старт

### Запуск теста RAG Flow

Тест демонстрирует полный цикл работы RAG:

```bash
# Из корня проекта
uv run python log_ai_agent/ai_agent_v2/test_rag_flow.py
```

**Что делает тест:**
1. Создаёт пайплайн с включённым RAG
2. **Agent 1** анализирует тестовые логи
3. RAG ищет релевантные техники MITRE ATT&CK
4. **Agent 2** формирует финальный отчёт
5. Выводит результат на русском языке

**Пример вывода:**
```
============================================================
  AI Agent v2 - RAG Flow Test
============================================================

📝 Creating pipeline with RAG...
✓ Pipeline created

[1] Agent 1: Primary Analysis
✓ Agent 1 found 2 events:
  - Повторяющиеся неудачные попытки входа
  - SQL-инъекция

[2] RAG: MITRE ATT&CK Search
✓ Found 5 MITRE techniques:
  1. T1110 (Brute Force)
  2. T1556.004 (Network Device Authentication)
  3. ...

[3] Agent 2: Final Report
  Severity: 2/4
  Threat Type: 5/11
  MITRE Techniques: ['T1110', 'T1190']

✅ RAG comparison is working!
```

---

## Использование в коде

### Базовый пример

```python
import asyncio
from log_ai_agent.ai_agent_v2 import create_pipeline
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config


async def analyze_logs():
    # Создание пайплайна
    pipeline = await create_pipeline(
        use_rag=True,  # Включить RAG
    )
    
    # Логи для анализа
    log_content = """
    2026-03-21 10:15:45 WARNING Failed login attempt for user admin from 192.168.1.100
    2026-03-21 10:15:46 WARNING Failed login attempt for user admin from 192.168.1.100
    2026-03-21 10:16:00 ERROR SQL syntax error near 'SELECT * FROM users WHERE id=1 OR 1=1--'
    """
    
    # Анализ
    result = await pipeline.analyze(
        log_content=log_content,
        config=get_callback_config(show_output=True),
    )
    
    if result.get("success"):
        stages = result.get("stages", {})
        
        # Результат Agent 1
        agent1 = stages.get("agent1", {})
        print(f"События: {agent1.get('events_found')}")
        print(f"Анализ: {agent1.get('primary_analysis')}")
        
        # Результат RAG
        rag = stages.get("rag", {})
        print(f"Техники MITRE: {rag.get('technique_ids')}")
        
        # Результат Agent 2
        agent2 = stages.get("agent2", {})
        print(f"Severity: {agent2.get('severity_level_id')}/4")
        print(f"Отчёт: {agent2.get('final_report')}")


if __name__ == "__main__":
    asyncio.run(analyze_logs())
```

### Создание пайплайна

```python
from log_ai_agent.ai_agent_v2 import create_pipeline

# С RAG
pipeline = await create_pipeline(use_rag=True)

# Без RAG (только Agent 1)
pipeline = await create_pipeline(use_rag=False)
```

### Callback конфигурация

```python
from log_ai_agent.ai_agent_v2.callbacks import get_callback_config

# Показать вывод в консоль
config = get_callback_config(show_output=True)

# Скрыть вывод
config = get_callback_config(show_output=False)

# Кастомные callback'и
config = get_callback_config(
    show_output=True,
    custom_callbacks=[your_callback_function],
)
```

---

## Как работает RAG

### 1. Инициализация базы знаний

При первом запуске `initialize_mitre_knowledge_base()`:

```
┌─────────────────────────────────────────┐
│  1. Проверка ChromaDB                   │
│     └─ Есть данные? → ГОТОВО            │
├─────────────────────────────────────────┤
│  2. Проверка локального JSON            │
│     └─ mitre_data/enterprise-attack.json│
│     └─ Есть? → Загрузить в ChromaDB     │
├─────────────────────────────────────────┤
│  3. Скачивание с GitHub                 │
│     └─ https://raw.githubusercontent.com│
│        /mitre/cti/master/enterprise-    │
│        attack/enterprise-attack.json    │
│     └─ Сохранить → Загрузить в ChromaDB │
└─────────────────────────────────────────┘
```

### 2. Поиск техник MITRE

```python
# В rag_chain.py
results = chroma_mgr.search(
    query="Brute force attack on admin account",
    k=5,  # Количество результатов
)

context = chroma_mgr.format_context(results)
# Возвращает отформатированный текст для LLM
```

### 3. Полный цикл анализа

```
┌──────────────┐
│   Agent 1    │  Первичный анализ логов
│              │  - Извлечение событий
│              │  - Структурирование
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  RAG Search  │  Поиск по MITRE ATT&CK
│              │  - Векторный поиск в ChromaDB
│              │  - Топ-5 техник
└─────────────┘
       │
       ▼
┌──────────────┐
│   Agent 2    │  Финальный отчёт
│              │  - Анализ Agent 1 + MITRE контекст
│              │  - Severity, Threat Type
│              │  - Отчёт на русском
└──────────────┘
```

---

## Тестирование

### Запуск всех тестов

```bash
# Тест RAG Flow (полный цикл)
uv run python log_ai_agent/ai_agent_v2/test_rag_flow.py

# Тест RAG (базовый)
uv run python log_ai_agent/ai_agent_v2/test_rag.py

# Быстрый тест
uv run python log_ai_agent/ai_agent_v2/test_quick.py
```

### Проверка загрузки MITRE

```bash
# Ручная загрузка MITRE в ChromaDB
uv run python log_ai_agent/ai_agent_v2/load_mitre_full.py

# Только скачивание JSON с GitHub
uv run python log_ai_agent/ai_agent_v2/download_mitre.py
```

### Проверка базы данных

```bash
# Проверка количества техник в ChromaDB
uv run python -c "
import chromadb
client = chromadb.PersistentClient(path='log_ai_agent/ai_agent_v2/chroma_db')
coll = client.get_collection('mitre_collection')
print(f'Техник в базе: {coll.count()}')
"
```

---

## MITRE ATT&CK

### Источники данных

- **GitHub**: [mitre/cti](https://github.com/mitre/cti)
  - Файл: `enterprise-attack/enterprise-attack.json`
  - Формат: STIX 2.1
  - Обновление: автоматическое при первом запуске

### Техники

База содержит ~835 техник MITRE ATT&CK Enterprise:

| Тактика | Примеры техник |
|---------|----------------|
| Credential Access | T1110 (Brute Force), T1556 (Modify Authentication) |
| Initial Access | T1190 (Exploit Public-Facing Application) |
| Execution | T1059 (Command and Scripting Interpreter) |
| Discovery | T1082 (System Information Discovery) |
| Exfiltration | T1041 (Exfiltration Over C2 Channel) |

### Обновление базы

Для обновления базы MITRE:

```bash
# Удалить существующую базу
rm -rf log_ai_agent/ai_agent_v2/chroma_db
rm -rf log_ai_agent/ai_agent_v2/mitre_data

# Запустить тест или скрипт (скачает заново)
uv run python log_ai_agent/ai_agent_v2/test_rag_flow.py
```

---

## Конфигурация

### ChromaDB

По умолчанию используется постоянная база данных:

```python
chroma_path = "log_ai_agent/ai_agent_v2/chroma_db"
collection_name = "mitre_collection"
```

### Эмбеддинги

Используется модель по умолчанию из `EmbeddingManager`:

```python
# В embedding/manager.py
DEFAULT_MODEL = "sentence-transformers/rubert-base-cased"
# или другая модель для русского языка
```

### LLM

GigaChat через `langchain-gigachat`:

```python
# В chains/agent1.py и chains/agent2.py
from langchain_gigachat.chat_models import GigaChat

llm = GigaChat(
    credentials=credentials,
    model="GigaChat",
    verify_ssl_certs=False,
)
```

---

## Устранение неполадок

### Ошибка: "Failed to load MITRE ATT&CK data"

**Причина**: Нет подключения к интернету при первом запуске.

**Решение**:
1. Проверить подключение к интернету
2. Скачать JSON вручную:
   ```bash
   uv run python log_ai_agent/ai_agent_v2/download_mitre.py
   ```
3. Запустить тест снова

### Ошибка: "ChromaDB not initialized"

**Причина**: База данных не инициализирована.

**Решение**:
```bash
# Удалить и пересоздать базу
rm -rf log_ai_agent/ai_agent_v2/chroma_db
uv run python log_ai_agent/ai_agent_v2/load_mitre_full.py
```

### Ошибка: "GigaChat credentials not found"

**Причина**: Не настроены переменные окружения.

**Решение**: Создать `.env` файл с credentials GigaChat.

---

## Лицензия

MITRE ATT&CK лицензируется в соответствии с [Terms of Use](https://attack.mitre.org/resources/terms-of-use/).

Данный модуль использует MITRE ATT&CK для образовательных и исследовательских целей.
