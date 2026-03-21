# Инструкция по установке и запуску AI Agent v2

## Требования

- Python 3.13
- Docker (опционально, для запуска с базой данных)
- GigaChat API ключ

## Установка зависимостей

### Вариант 1: Через uv (рекомендуется)

```bash
cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent

# Установить зависимости
uv sync

# Если есть проблемы с сетью, установить по отдельности:
uv pip install aiohttp tenacity
```

### Вариант 2: Через pip

```bash
cd C:\Users\litsu\PycharmProjects\AI-CyberLogAgent

# Активировать venv
.venv\Scripts\activate

# Установить новые зависимости
pip install aiohttp==3.11.11 tenacity==9.0.0
```

## Настройка

1. Создать файл `.env` в папке `log_ai_agent/` на основе `.env.example`

2. Указать GigaChat API ключ:
```
GIGACHAT_API_KEY=ваш_ключ
```

## Инициализация базы знаний MITRE ATT&CK

Первый запуск требует загрузки MITRE ATT&CK в ChromaDB:

```python
# init_mitre.py
from log_ai_agent.ai_agent_v2.rag.mitre_loader import initialize_mitre_knowledge_base

if __name__ == "__main__":
    print("Инициализация базы знаний MITRE ATT&CK...")
    
    chroma_mgr = initialize_mitre_knowledge_base(
        chroma_path="log_ai_agent/ai_agent_v2/chroma_db",
        embedding_model="sentence-transformers/rubert-base-cased",
        domain="enterprise-attack",
    )
    
    print("✓ База знаний инициализирована!")
    print(f"  Путь: {chroma_mgr.chroma_path}")
```

Запуск:
```bash
python -m log_ai_agent.ai_agent_v2.rag.mitre_loader
```

## Запуск сервера

```bash
cd log_ai_agent
python app.py
```

Сервер запустится на `http://localhost:8000`

## Тестирование API

### Загрузка лога на анализ (AI Agent v2)

```bash
curl -X POST "http://localhost:8000/api/logs/upload?user_id=1&use_v2=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.log"
```

### Через Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/logs/upload",
    params={"user_id": 1, "use_v2": True},
    files={"file": open("sample.log", "rb")},
)

print(response.json())
```

## Запуск тестов

```bash
# Установить pytest и pytest-asyncio
pip install pytest pytest-asyncio

# Запустить тесты
pytest log_ai_agent/ai_agent_v2/tests/ -v
```

## Отладка

### Включить debug логирование

В начало `app.py` добавить:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Проверка RAG

```python
from log_ai_agent.ai_agent_v2.rag.chroma_manager import ChromaManager

chroma = ChromaManager()
chroma.initialize()

# Поиск техник
results = chroma.search("SQL injection", k=3)
for r in results:
    print(f"{r['metadata']['technique_id']}: {r['metadata']['technique_name']}")
```

## Возможные проблемы

### 1. Ошибка "Local embeddings not available"

RAG работает в fallback режиме. Для полноценной работы:
- Скачать модель эмбеддингов
- Указать путь в `ChromaManager`

### 2. Таймаут GigaChat API

Увеличить таймаут в `GigaChatClient`:
```python
client = GigaChatClient(timeout=120)
```

### 3. ChromaDB не инициализируется

Проверить наличие прав на запись в папку `chroma_db/`

## Миграция со старой версии

Старый AI модуль (`ai_agent/gigachat.py`) сохраняется для обратной совместимости.

Для использования v2 в API:
```bash
curl -X POST "http://localhost:8000/api/logs/upload?user_id=1&use_v2=true" ...
```

Для использования v1 (legacy):
```bash
curl -X POST "http://localhost:8000/api/logs/upload?user_id=1&use_v2=false" ...
```

## Дополнительная документация

- [README модуля](ai_agent_v2/README.md)
- [Функциональная спецификация](../../FUNCTIONAL_SPECIFICATION.md)
