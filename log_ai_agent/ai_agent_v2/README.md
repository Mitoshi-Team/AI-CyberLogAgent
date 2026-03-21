# AI Agent v2 - Log Analysis Pipeline

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│  Агент 1: Первичный анализ логов                             │
│  - Получает сырые логи                                        │
│  - Ищет аномалии, паттерны атак                               │
│  - Составляет мини-отчёт (что найдено)                        │
└──────────────────────────────────────────────────────────────┘
                          ↓
                    [Мини-отчёт]
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  RAG Engine: Сопоставление с MITRE ATT&CK                    │
│  - Поиск техник по описанию из мини-отчёта                    │
│  - Возвращает релевантные техники MITRE                       │
└──────────────────────────────────────────────────────────────┘
                          ↓
              [Мини-отчёт + MITRE контекст]
                          ↓
┌──────────────────────────────────────────────────────────────┐
│  Агент 2: Финальный отчёт                                    │
│  - Получает мини-отчёт + MITRE техники                        │
│  - Формирует итоговый отчёт                                   │
│  - Определяет severity, threat_type                           │
│  - Даёт рекомендации                                          │
└──────────────────────────────────────────────────────────────┘
```

## Структура модуля

```
ai_agent_v2/
├── __init__.py                 # Экспорт основных классов
├── gigachat_client.py          # Async клиент GigaChat API
├── integration.py              # Интеграция с FastAPI app
├── prompts/
│   ├── system.py               # Системные промпты
│   └── log_analysis.py         # Промпты для анализа логов
├── rag/
│   ├── chroma_manager.py       # Управление ChromaDB
│   ├── mitre_loader.py         # Загрузка MITRE ATT&CK
│   └── retriever.py            # Поиск контекста
├── pipeline/
│   └── analyzer.py             # Основной пайплайн анализа
├── models/
│   └── schemas.py              # Pydantic модели
└── tests/
    └── test_pipeline.py        # Тесты
```

## Быстрый старт

### 1. Установка зависимостей

```bash
cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent
uv sync
```

### 2. Инициализация базы знаний MITRE ATT&CK

```python
from log_ai_agent.ai_agent_v2.rag.mitre_loader import initialize_mitre_knowledge_base

# Инициализация ChromaDB с MITRE ATT&CK
chroma_mgr = initialize_mitre_knowledge_base(
    chroma_path="log_ai_agent/ai_agent_v2/chroma_db",
    embedding_model="sentence-transformers/rubert-base-cased",
    domain="enterprise-attack",
)
```

### 3. Использование пайплайна

```python
import asyncio
from log_ai_agent.ai_agent_v2 import GigaChatClient, LogAnalysisPipeline

async def analyze_log():
    # Инициализация клиента
    client = GigaChatClient(
        temperature=0.1,
        max_tokens=4000,
        timeout=90,
    )
    
    # Создание пайплайна
    pipeline = LogAnalysisPipeline(
        gigachat_client=client,
        chroma_manager=None,  # Или chroma_mgr если RAG доступен
        use_rag=False,  # Или True если RAG настроен
    )
    
    # Анализ лога
    with open("sample.log", "r") as f:
        log_content = f.read()
    
    result = await pipeline.analyze_log(log_content)
    
    if result.success:
        print(f"Отчёт: {result.final_result.report_text}")
        print(f"Severity: {result.final_result.severity_level_id}")
        print(f"Threat: {result.final_result.threat_type_id}")
    else:
        print(f"Ошибка: {result.final_result.error_message}")

asyncio.run(analyze_log())
```

### 4. Через API

```bash
# Загрузка лога с использованием AI Agent v2
curl -X POST "http://localhost:8000/api/logs/upload?user_id=1&use_v2=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.log"
```

## Конфигурация

### GigaChat Client

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `api_key` | из `.env` | GigaChat API ключ |
| `model` | `"GigaChat"` | Модель для использования |
| `temperature` | `0.1` | Температура генерации (0.0-1.0) |
| `max_tokens` | `4000` | Максимум токенов в ответе |
| `timeout` | `60` | Таймаут запроса в секундах |
| `max_retries` | `3` | Максимум попыток при ошибке |
| `rate_limit_delay` | `0.5` | Задержка между запросами (сек) |

### RAG настройки

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `embedding_model` | `rubert-base-cased` | Модель эмбеддингов |
| `chroma_path` | `./chroma_db` | Путь к хранилищу ChromaDB |
| `collection_name` | `mitre_collection` | Имя коллекции |
| `top_k` | `5` | Количество техник для поиска |

## Тестирование

```bash
# Запуск тестов
pytest log_ai_agent/ai_agent_v2/tests/ -v

# Запуск с покрытием
pytest log_ai_agent/ai_agent_v2/tests/ --cov=ai_agent_v2
```

## Отличия от v1

| Характеристика | v1 | v2 |
|----------------|----|----|
| Клиент GigaChat | Синхронный | Асинхронный |
| Retry логика | Отсутствует | Exponential backoff |
| RAG | Не работает | ChromaDB + MITRE |
| Архитектура | Один агент | 2 агента + RAG |
| Логирование | Минимальное | Полное на всех этапах |
| Тесты | Отсутствуют | Покрытие >80% |

## Pipeline этапы

1. **Agent 1 (Primary Analysis)**
   - Получает сырые логи
   - Ищет аномалии и паттерны атак
   - Возвращает структурированный мини-отчёт

2. **RAG (MITRE Search)**
   - Извлекает ключевые слова из мини-отчёта
   - Ищет релевантные техники в MITRE ATT&CK
   - Возвращает контекст с тактиками и техниками

3. **Agent 2 (Final Report)**
   - Получает мини-отчёт + MITRE контекст
   - Формирует итоговый отчёт
   - Определяет severity (1-4) и threat_type (1-11)
   - Извлекает метаданные из ответа

## Обработка ошибок

- **Timeout**: Если анализ занимает >120сек, возвращается ошибка
- **API ошибки**: Автоматические retry с экспоненциальной задержкой
- **RAG недоступен**: Пайплайн работает в fallback режиме (без RAG)
- **Парсинг метаданных**: При ошибке используются значения по умолчанию

## Лицензия

MIT
