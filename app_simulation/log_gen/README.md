# 📝 Генератор логов AI-CyberLogAgent

Профессиональный генератор реалистичных Apache/mod_jk логов с поддержкой симуляции инцидентов безопасности.

## 🎯 Возможности

- ✅ **Реалистичные логи** - основаны на реальных Apache логах из [loghub](https://github.com/logpai/loghub)
- ✅ **9 типов логов** - worker init/errors, jk2 children, client errors, system notices и другие
- ✅ **7 типов инцидентов** - worker errors, memory leaks, crashes, атаки и другие
- ✅ **Гибкая настройка** - JSON конфигурация с весами для каждого типа лога
- ✅ **Готовые конфигурации** - 6 предустановленных сценариев (атака, стабильная работа, отладка и др.)
- ✅ **Статистика** - подробная информация о сгенерированных логах
- ✅ **Экспорт в .log** - сохранение в стандартном формате Apache

## 🚀 Быстрый старт

### Базовое использование

```bash
# Генерация с готовой конфигурацией
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --output output.log

# Генерация с кастомными параметрами
python -m log_gen.cli -o output.log -n 500 -e 0.2 -i 0.1 --show-stats

# Предпросмотр без сохранения
python -m log_gen.cli --preview -n 50
```

### Готовые конфигурации

```bash
# Реалистичная смешанная (рекомендуется)
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --output analyse_logs.log

# Симуляция атаки
python -m log_gen.cli --config log_gen/configs/attack.json --output attack.log

# Стабильная работа сервера
python -m log_gen.cli --config log_gen/configs/stable.json --output stable.log

# Запуск/перезапуск сервера
python -m log_gen.cli --config log_gen/configs/startup.json --output startup.log

# Отладка worker процессов
python -m log_gen.cli --config log_gen/configs/debug_workers.json --output debug.log

# Высокая нагрузка
python -m log_gen.cli --config log_gen/configs/high_load.json --output high_load.log
```

Подробнее о конфигурациях см. [configs/README.md](configs/README.md)

### Создание своей конфигурации

```bash
# Создать шаблон конфигурации
python -m log_gen.cli --create-config my_config.json

# Отредактировать my_config.json (веса типов логов, IP диапазоны, пути и др.)

# Использовать конфигурацию
python -m log_gen.cli -c my_config.json -o output.log
```

Подробное руководство по настройке: [CONFIGURATION.md](CONFIGURATION.md)

### Генерация специфичных инцидентов

```bash
# Только worker errors
python -m log_gen.cli -o incidents.log -n 50 --incident-only worker_error

# Только service crashes
python -m log_gen.cli -o crashes.log -n 30 --incident-only service_crash
```

## 📚 Структура модуля

```
log_gen/
├── __init__.py          # Экспорт публичного API
├── log_gen.py           # Основной генератор логов
├── config_loader.py     # Загрузчик конфигурации
├── cli.py               # CLI интерфейс
├── examples.py          # Примеры использования
├── README.md            # Эта документация
├── CONFIGURATION.md     # Подробное руководство по конфигурации
└── configs/             # Готовые конфигурации
    ├── README.md
    ├── realistic_mixed.json
    ├── attack.json
    ├── stable.json
    ├── startup.json
    ├── debug_workers.json
    └── high_load.json
```

## 🔧 Параметры CLI

| Параметр | Короткий | Описание | Значение по умолчанию |
|----------|----------|----------|----------------------|
| `--output` | `-o` | Путь к выходному .log файлу | - |
| `--log-count` | `-n` | Количество логов | 100 |
| `--error-probability` | `-e` | Вероятность ошибки (0.0-1.0) | 0.15 |
| `--incident-probability` | `-i` | Вероятность инцидента (0.0-1.0) | 0.05 |
| `--config` | `-c` | Путь к JSON конфигурации | - |
| `--create-config` | - | Создать шаблон конфигурации | - |
| `--incident-only` | - | Генерировать только указанный тип инцидента | - |
| `--time-range` | - | Диапазон секунд между логами | [1, 30] |
| `--show-stats` | - | Показать статистику | False |
| `--preview` | - | Предпросмотр без сохранения | False |

## 📝 Типы логов

Генератор поддерживает 9 типов логов, основанных на реальных Apache логах:

| Тип | Уровень | Пример |
|-----|---------|--------|
| `normal` | INFO/NOTICE | `jk2_init() Found child 6725 in scoreboard slot 10` |
| `error` | ERROR | `mod_jk child workerEnv in error state 6` |
| `mod_jk_worker_init` | NOTICE | `workerEnv.init() ok /etc/httpd/conf/workers2.properties` |
| `mod_jk_worker_error` | ERROR | `mod_jk child workerEnv in error state 8` |
| `jk2_child_init` | NOTICE | `jk2_init() Found child 6825 in scoreboard slot 5` |
| `jk2_child_error` | ERROR | `jk2_init() Can't find child 6900 in scoreboard` |
| `client_directory_forbidden` | ERROR | `[client 192.168.1.100] Directory index forbidden by rule: /var/www/html/` |
| `client_file_not_found` | ERROR | `[client 10.0.0.5] File does not exist: /var/www/html/missing.php` |
| `system_notice` | NOTICE | `Apache/2.2.3 configured -- resuming normal operations` |

Настройка весов типов логов в [CONFIGURATION.md](CONFIGURATION.md)

## � Типы инцидентов

| Тип | Описание | Серьёзность |
|-----|----------|-------------|
| `worker_error` | Критические ошибки worker процессов | Высокая |
| `connection_failed` | Проблемы с подключением к backend | Высокая |
| `memory_leak` | Утечки памяти в процессах | Критическая |
| `service_crash` | Критические падения сервиса (segfault) | Критическая |
| `auth_failure` | Провалы аутентификации, brute-force | Средняя |
| `permission_denied` | Отказы в доступе, нарушения безопасности | Средняя |
| `resource_exhaustion` | Исчерпание ресурсов (MaxClients, file descriptors) | Высокая |

## 💻 Использование как библиотеки

### Простой пример

```python
from app_simulation.log_gen import LogGenerator, GeneratorConfig, IncidentType

# Создание конфигурации
config = GeneratorConfig(
    log_count=100,
    error_probability=0.2,
    incident_probability=0.1,
)

# Генерация логов
generator = LogGenerator(config)
logs = generator.generate_logs()

# Сохранение в файл
generator.save_to_file("output.log")

# Или получение строки
log_text = generator.get_formatted_logs()
print(log_text)
```

### Генерация специфичных инцидентов

```python
from app_simulation.log_gen import LogGenerator, IncidentType

generator = LogGenerator()

# Генерация одного инцидента
incident_logs = generator.generate_incident(IncidentType.MEMORY_LEAK)

# Сохранение
generator.logs = incident_logs
generator.save_to_file("memory_leak_incident.log")
```

## 🎨 Пример конфигурации (JSON)

```json
{
  "log_count": 500,
  "time_increment_seconds": [5, 60],
  "process_id_range": [5000, 8000],
  "slot_range": [1, 15],
  "error_probability": 0.25,
  "incident_probability": 0.08,
  "incident_types": [
    "worker_error",
    "connection_failed",
    "service_crash"
  ],
  "incident_duration_logs": [5, 15]
}
```

## 📊 Пример вывода

```
[Thu Dec 04 21:17:49 2025] [notice] Server built: Dec 04 2025 21:17:49
[Thu Dec 04 21:17:53 2025] [error] Child 6981: Encountered too many errors accepting client connections
[Thu Dec 04 21:18:05 2025] [notice] prefork.c: Child process 6378 is entering scoreboard slot 6
[Thu Dec 04 21:19:00 2025] [error] Permission denied: user 'root' cannot access /etc/passwd
[Thu Dec 04 21:19:16 2025] [error] Access forbidden for 152.50.238.244: insufficient privileges
[Thu Dec 04 21:19:34 2025] [crit] Segmentation fault in worker process 6050
```

## 🏗️ Архитектура

### Классы

#### `LogLevel` (Enum)
Уровни логирования: NOTICE, ERROR, WARN, CRITICAL, INFO, DEBUG

#### `IncidentType` (Enum)
Типы инцидентов для генерации

#### `LogEntry` (Dataclass)
Представление одной записи лога с методом форматирования

#### `GeneratorConfig` (Dataclass)
Конфигурация генератора со всеми параметрами

#### `LogGenerator`
Основной класс генератора с методами:
- `generate_normal_log()` - генерация обычного лога
- `generate_error_log()` - генерация ошибки
- `generate_incident()` - генерация инцидента
- `generate_logs()` - генерация набора логов
- `save_to_file()` - сохранение в файл

#### `ConfigLoader`
Загрузчик конфигурации из JSON с валидацией

## ✨ Особенности реализации

- **OOP принципы** - чистая архитектура с разделением ответственности
- **Type hints** - полная типизация для Python 3.13+
- **Docstrings** - подробная документация всех методов
- **PEP 8** - соответствие стандартам оформления
- **DRY** - отсутствие дублирования кода
- **Extensibility** - легко расширяемая архитектура

## 🔮 Roadmap

- [ ] YAML конфигурация
- [ ] Дополнительные форматы логов (syslog, JSON)
- [ ] Генерация access логов
- [ ] Паттерны временных серий
- [ ] Web интерфейс для конфигурации

## 📄 Лицензия

AI-CyberLogAgent Project © 2025
