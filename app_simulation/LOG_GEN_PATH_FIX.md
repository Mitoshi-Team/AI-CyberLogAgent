# 🔧 Исправление путей в генераторе логов

## Проблема

После переноса `log_gen_cli.py` в директорию `app_simulation/log_gen/` возникали ошибки:
1. ❌ Дублирование путей: `app_simulation/log_gen/app_simulation/log_gen/configs/...`
2. ❌ Абсолютные импорты не работали внутри модуля
3. ❌ Файл `log_gen.py` был переименован в `old_old_old_log_gen.py`

## Решение

### 1. Исправлены пути к конфигурациям

**Было (абсолютные пути):**
```python
CONFIG_MAP = {
    "attack": "app_simulation/log_gen/configs/attack.json",
    ...
}
```

**Стало (относительные пути через Path):**
```python
CURRENT_DIR = Path(__file__).parent

CONFIG_MAP = {
    "attack": CURRENT_DIR / "configs" / "attack.json",
    "realistic": CURRENT_DIR / "configs" / "realistic_mixed.json",
    "stable": CURRENT_DIR / "configs" / "stable.json",
    "load": CURRENT_DIR / "configs" / "high_load.json",
}

OUTPUT_LOG_FILE = CURRENT_DIR / "logs.log"
```

### 2. Исправлены импорты на относительные

**config_loader.py:**
```python
# Было:
from log_gen import GeneratorConfig, IncidentType, LogType

# Стало:
from .log_gen import GeneratorConfig, IncidentType, LogType
```

**log_gen_cli.py:**
```python
# Было:
from config_loader import ConfigLoader
from log_gen import LogGenerator

# Стало:
from .config_loader import ConfigLoader
from .log_gen import LogGenerator
```

### 3. Восстановлен файл log_gen.py

```bash
cd app_simulation/log_gen
mv old_old_old_log_gen.py log_gen.py
```

## Результаты тестирования

### ✅ Все команды работают:

```bash
# Помощь
python -m app_simulation.log_gen.log_gen_cli --help

# Генерация логов
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack 20
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests realistic 30
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable 25
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests load 15
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack  # 500 по умолчанию
```

### 📊 Результаты тестов:

| Конфигурация | Логов запрошено | Сгенерировано | Error % | Статус |
|--------------|----------------|---------------|---------|---------|
| attack       | 20             | 20            | 100%    | ✅      |
| realistic    | 30             | 34            | 47.1%   | ✅      |
| stable       | 25             | 25            | 12.0%   | ✅      |
| load         | 15             | 15            | 93.3%   | ✅      |
| attack (def) | 500            | 517           | 76.4%   | ✅      |

### ✅ Проверка качества кода:

```bash
uv run ruff check app_simulation/log_gen/log_gen_cli.py
uv run ruff check app_simulation/log_gen/config_loader.py
```

**Результат:** All checks passed! ✅

## Правильное использование

**Важно:** Команды нужно запускать из **корня проекта** `AI-CyberLogAgent/`:

```bash
# ✅ Правильно (из корня проекта)
cd AI-CyberLogAgent
python -m app_simulation.log_gen.log_gen_cli start imitate attack

# ❌ Неправильно (из директории log_gen)
cd app_simulation/log_gen
python log_gen_cli.py start imitate attack  # ModuleNotFoundError
```

## Выходные файлы

**Путь:** `app_simulation/log_gen/logs.log`

**Формат:**
```log
# Log generation started: 2025-12-08 19:30:19
# Mode: record_logs_for_tests
# Config: attack
# Total logs: 500

[Mon Dec 08 19:30:22 2025] [error] Child 6708: Encountered too many errors...
[Mon Dec 08 19:30:24 2025] [error] [client 30.110.16.44] File does not exist...
```

## Технические детали

### Почему используем Path(__file__).parent?

```python
CURRENT_DIR = Path(__file__).parent
```

- `__file__` - полный путь к текущему файлу `.py`
- `.parent` - директория, содержащая файл
- Это делает пути относительными и работающими независимо от того, откуда запущен скрипт

### Почему относительные импорты?

```python
from .config_loader import ConfigLoader
```

- Работают только при запуске через `-m` (как модуль)
- Обеспечивают правильное разрешение зависимостей внутри пакета
- Соответствуют Python best practices

## Итоговая структура

```
AI-CyberLogAgent/
├── app_simulation/
│   ├── __init__.py
│   └── log_gen/
│       ├── __init__.py
│       ├── log_gen.py           ← Восстановлен
│       ├── log_gen_cli.py       ← Исправлены пути и импорты
│       ├── config_loader.py     ← Исправлены импорты
│       ├── configs/
│       │   ├── attack.json
│       │   ├── realistic_mixed.json
│       │   ├── stable.json
│       │   └── high_load.json
│       └── logs.log             ← Выходной файл
```

---

**Дата исправления:** 8 декабря 2025  
**Статус:** ✅ Полностью исправлено и протестировано
