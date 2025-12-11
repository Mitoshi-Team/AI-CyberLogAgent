# Конфигурация генератора логов

Этот документ описывает, как настраивать генератор Apache логов через JSON-конфигурацию.

## Оглавление

- [Обзор](#обзор)
- [Основные параметры](#основные-параметры)
- [Типы логов и их веса](#типы-логов-и-их-веса)
- [Настройка IP адресов](#настройка-ip-адресов)
- [Настройка путей](#настройка-путей)
- [Настройка инцидентов](#настройка-инцидентов)
- [Примеры конфигураций](#примеры-конфигураций)

## Обзор

Генератор логов использует JSON-файл для настройки всех аспектов генерации. Это позволяет создавать реалистичные логи Apache с различными характеристиками без изменения кода.

### Создание базовой конфигурации

```bash
python -m log_gen.config_loader
```

Эта команда создаст файл `log_generator_config.json` с настройками по умолчанию.

## Основные параметры

### `log_count` (integer)
**Обязательный:** Нет  
**Значение по умолчанию:** 100  
**Описание:** Количество логов для генерации

```json
{
  "log_count": 500
}
```

### `time_increment_seconds` (array[min, max])
**Обязательный:** Нет  
**Значение по умолчанию:** [1, 30]  
**Описание:** Диапазон секунд между последовательными логами

```json
{
  "time_increment_seconds": [5, 60]
}
```

Это создаст логи с интервалом от 5 до 60 секунд.

### `process_id_range` (array[min, max])
**Обязательный:** Нет  
**Значение по умолчанию:** [6000, 7000]  
**Описание:** Диапазон ID процессов для генерации

```json
{
  "process_id_range": [5000, 8000]
}
```

### `slot_range` (array[min, max])
**Обязательный:** Нет  
**Значение по умолчанию:** [1, 10]  
**Описание:** Диапазон номеров слотов для jk2_child процессов

```json
{
  "slot_range": [1, 20]
}
```

### `start_time` (string, ISO format)
**Обязательный:** Нет  
**Значение по умолчанию:** текущее время  
**Описание:** Начальное время для первого лога

```json
{
  "start_time": "2024-01-15T10:00:00"
}
```

## Типы логов и их веса

### `log_type_weights` (object)

**КРИТИЧЕСКИ ВАЖНО:** Веса определяют, как часто генерируется каждый тип лога. Сумма всех весов должна быть **1.0** (100%).

#### Доступные типы логов:

| Тип лога | Описание | Пример |
|----------|----------|--------|
| `normal` | Обычные информационные логи | `jk2_init() Found child 6725 in scoreboard slot 10` |
| `error` | Общие ошибки | `mod_jk child workerEnv in error state 6` |
| `mod_jk_worker_init` | Инициализация mod_jk worker | `workerEnv.init() ok /etc/httpd/conf/workers2.properties` |
| `mod_jk_worker_error` | Ошибки mod_jk worker | `mod_jk child workerEnv in error state 8` |
| `jk2_child_init` | Инициализация jk2 child процесса | `jk2_init() Found child 6825 in scoreboard slot 5` |
| `jk2_child_error` | Ошибки jk2 child процесса | `jk2_init() Can't find child 6900 in scoreboard` |
| `client_directory_forbidden` | Запрещённый доступ к директории | `[client 192.168.1.100] Directory index forbidden by rule: /var/www/html/` |
| `client_file_not_found` | Файл не найден | `[client 10.0.0.5] File does not exist: /var/www/html/missing.php` |
| `system_notice` | Системные уведомления | `Apache/2.2.3 configured -- resuming normal operations` |

#### Пример конфигурации весов:

```json
{
  "log_type_weights": {
    "normal": 0.4,
    "error": 0.1,
    "mod_jk_worker_init": 0.05,
    "mod_jk_worker_error": 0.05,
    "jk2_child_init": 0.1,
    "jk2_child_error": 0.05,
    "client_directory_forbidden": 0.1,
    "client_file_not_found": 0.1,
    "system_notice": 0.05
  }
}
```

Эта конфигурация означает:
- 40% — обычные логи
- 10% — ошибки
- 5% — инициализация mod_jk worker
- 5% — ошибки mod_jk worker
- 10% — инициализация jk2 child
- 5% — ошибки jk2 child
- 10% — запрещённый доступ к директориям
- 10% — файлы не найдены
- 5% — системные уведомления

### Предустановленные профили весов

#### Высокая нагрузка с ошибками
```json
{
  "log_type_weights": {
    "normal": 0.3,
    "error": 0.2,
    "mod_jk_worker_error": 0.15,
    "jk2_child_error": 0.1,
    "client_directory_forbidden": 0.15,
    "client_file_not_found": 0.1
  }
}
```

#### Чистая работа (минимум ошибок)
```json
{
  "log_type_weights": {
    "normal": 0.6,
    "mod_jk_worker_init": 0.15,
    "jk2_child_init": 0.15,
    "system_notice": 0.1
  }
}
```

#### Фокус на клиентских ошибках
```json
{
  "log_type_weights": {
    "normal": 0.3,
    "client_directory_forbidden": 0.35,
    "client_file_not_found": 0.35
  }
}
```

## Настройка IP адресов

### `client_ip_ranges` (array of strings)

Определяет, из каких диапазонов генерировать IP адреса клиентов для ошибок доступа.

#### Поддерживаемые форматы:

1. **CIDR нотация** — для частных сетей:
   - `192.168.0.0/16` — диапазон 192.168.0.0 - 192.168.255.255
   - `10.0.0.0/8` — диапазон 10.0.0.0 - 10.255.255.255
   - `172.16.0.0/12` — диапазон 172.16.0.0 - 172.31.255.255

2. **Ключевое слово `"public"`** — для публичных IP адресов (1.0.0.0 - 255.255.255.255, исключая частные диапазоны)

#### Примеры:

**Только локальная сеть:**
```json
{
  "client_ip_ranges": ["192.168.0.0/16"]
}
```

**Смешанные источники:**
```json
{
  "client_ip_ranges": [
    "192.168.0.0/16",
    "10.0.0.0/8",
    "public"
  ]
}
```

**Только публичные IP:**
```json
{
  "client_ip_ranges": ["public"]
}
```

## Настройка путей

### `forbidden_paths` (array of strings)

Список путей, которые будут использоваться в логах ошибок доступа (`client_directory_forbidden`, `client_file_not_found`).

#### Пример:

```json
{
  "forbidden_paths": [
    "/var/www/html/",
    "/var/www/html/admin/",
    "/var/www/html/images/",
    "/var/www/html/uploads/",
    "/usr/local/apache/htdocs/",
    "/opt/webapp/public/",
    "/home/www/site/private/"
  ]
}
```

#### Рекомендации:

- Используйте реалистичные пути для вашего сценария
- Добавляйте пути с повышенной безопасностью (admin, private, uploads)
- Завершайте директории слэшем `/`

## Настройка инцидентов

### `incident_probability` (float, 0.0 - 1.0)
**Значение по умолчанию:** 0.05 (5%)  
**Описание:** Вероятность генерации инцидента вместо обычного лога

```json
{
  "incident_probability": 0.1
}
```

### `incident_types` (array of strings)

Типы инцидентов, которые могут быть сгенерированы.

#### Доступные типы инцидентов:

| Тип | Описание | Серьёзность |
|-----|----------|-------------|
| `worker_error` | Критическая ошибка worker процесса | Высокая |
| `connection_failed` | Неудачное подключение к backend серверу | Высокая |
| `memory_leak` | Утечка памяти в процессе | Критическая |
| `service_crash` | Крах сервиса (segfault, сигналы) | Критическая |
| `auth_failure` | Неудачная аутентификация | Средняя |
| `permission_denied` | Отказ в доступе | Средняя |
| `resource_exhaustion` | Исчерпание ресурсов (файлы, сокеты) | Высокая |

#### Пример:

```json
{
  "incident_types": [
    "worker_error",
    "connection_failed",
    "memory_leak"
  ]
}
```

### `incident_duration_logs` (array[min, max])
**Значение по умолчанию:** [3, 10]  
**Описание:** Количество логов в одном инциденте

```json
{
  "incident_duration_logs": [5, 15]
}
```

Инциденты будут содержать от 5 до 15 связанных логов.

### `error_probability` (float, 0.0 - 1.0)
**Значение по умолчанию:** 0.15 (15%)  
**Описание:** Вероятность генерации обычной ошибки

```json
{
  "error_probability": 0.2
}
```

**Примечание:** `error_probability` работает только когда `incident_probability` не сработал. Логика: сначала проверяется инцидент, затем ошибка, затем используются `log_type_weights`.

## Примеры конфигураций

### 1. Конфигурация "Высокая нагрузка"

Сценарий: Сервер под большой нагрузкой с частыми ошибками клиентов.

```json
{
  "log_count": 1000,
  "time_increment_seconds": [1, 5],
  "incident_probability": 0.15,
  "error_probability": 0.25,
  "log_type_weights": {
    "normal": 0.25,
    "error": 0.15,
    "mod_jk_worker_error": 0.1,
    "jk2_child_error": 0.1,
    "client_directory_forbidden": 0.2,
    "client_file_not_found": 0.2
  },
  "client_ip_ranges": ["public"],
  "forbidden_paths": [
    "/var/www/html/",
    "/var/www/html/admin/",
    "/var/www/html/api/"
  ],
  "incident_types": [
    "worker_error",
    "connection_failed",
    "resource_exhaustion"
  ]
}
```

### 2. Конфигурация "Стабильная работа"

Сценарий: Нормально работающий сервер с редкими ошибками.

```json
{
  "log_count": 500,
  "time_increment_seconds": [10, 60],
  "incident_probability": 0.02,
  "error_probability": 0.05,
  "log_type_weights": {
    "normal": 0.5,
    "mod_jk_worker_init": 0.15,
    "jk2_child_init": 0.2,
    "system_notice": 0.1,
    "client_directory_forbidden": 0.03,
    "client_file_not_found": 0.02
  },
  "client_ip_ranges": [
    "192.168.0.0/16",
    "10.0.0.0/8"
  ],
  "forbidden_paths": [
    "/var/www/html/"
  ]
}
```

### 3. Конфигурация "Атака"

Сценарий: Активная попытка взлома с большим количеством запросов к запрещённым ресурсам.

```json
{
  "log_count": 2000,
  "time_increment_seconds": [1, 3],
  "incident_probability": 0.2,
  "error_probability": 0.3,
  "log_type_weights": {
    "normal": 0.1,
    "error": 0.2,
    "client_directory_forbidden": 0.4,
    "client_file_not_found": 0.3
  },
  "client_ip_ranges": ["public"],
  "forbidden_paths": [
    "/var/www/html/admin/",
    "/var/www/html/config/",
    "/var/www/html/.git/",
    "/var/www/html/backup/",
    "/var/www/html/uploads/shell.php",
    "/etc/passwd",
    "/etc/shadow"
  ],
  "incident_types": [
    "auth_failure",
    "permission_denied",
    "resource_exhaustion"
  ]
}
```

### 4. Конфигурация "Запуск сервера"

Сценарий: Первый запуск или перезапуск сервера с инициализацией.

```json
{
  "log_count": 200,
  "time_increment_seconds": [1, 10],
  "incident_probability": 0.01,
  "error_probability": 0.05,
  "log_type_weights": {
    "mod_jk_worker_init": 0.3,
    "jk2_child_init": 0.3,
    "system_notice": 0.3,
    "normal": 0.1
  },
  "client_ip_ranges": [],
  "forbidden_paths": []
}
```

### 5. Конфигурация "Debugging"

Сценарий: Отладка с фокусом на ошибки worker процессов.

```json
{
  "log_count": 300,
  "time_increment_seconds": [2, 15],
  "incident_probability": 0.3,
  "error_probability": 0.2,
  "log_type_weights": {
    "normal": 0.2,
    "mod_jk_worker_init": 0.2,
    "mod_jk_worker_error": 0.3,
    "jk2_child_init": 0.1,
    "jk2_child_error": 0.2
  },
  "client_ip_ranges": ["192.168.1.0/24"],
  "forbidden_paths": ["/var/www/html/"],
  "incident_types": [
    "worker_error",
    "memory_leak",
    "service_crash"
  ],
  "incident_duration_logs": [5, 20]
}
```

## Использование конфигурации

### Через CLI

```bash
# Создать конфигурацию по умолчанию
python -m log_gen.cli --create-config my_config.json

# Сгенерировать логи с конфигурацией
python -m log_gen.cli --config my_config.json --output analyse_logs/output.log
```

### Через Python код

```python
from pathlib import Path
from app_simulation.log_gen import ConfigLoader, LogGenerator

# Загрузить конфигурацию
config = ConfigLoader.load_from_json("my_config.json")

# Создать генератор
generator = LogGenerator(config)

# Генерировать логи
logs = generator.generate_logs()

# Сохранить в файл
generator.save_to_file(Path("output.log"))
```

## Валидация конфигурации

При загрузке конфигурации автоматически проверяются:

1. **Сумма весов:** `log_type_weights` должны суммироваться в 1.0 (допустимая погрешность ±0.01)
2. **Диапазоны:** все `[min, max]` массивы должны иметь `min < max`
3. **Вероятности:** все probability поля должны быть в диапазоне 0.0 - 1.0
4. **Типы инцидентов:** все указанные типы должны существовать
5. **Типы логов:** все типы в `log_type_weights` должны быть валидными

## Советы по настройке

### Реалистичность
- Используйте логи из реальных Apache серверов как эталон
- Смешивайте различные типы логов с правдоподобными пропорциями
- Настройте временные интервалы в соответствии с реальной нагрузкой

### Производительность
- Для больших объёмов (>10000 логов) увеличьте `time_increment_seconds`
- Уменьшите `incident_probability` для больших объёмов

### Безопасность и тестирование
- Для тестирования систем обнаружения вторжений используйте высокие веса для ошибок клиентов
- Настройте `forbidden_paths` с чувствительными путями вашей системы
- Используйте реальные CIDR диапазоны вашей сети

### Отладка
- Начните с малого `log_count` (50-100) для быстрого тестирования
- Используйте специфичные `incident_types` для тестирования обработки конкретных сценариев

## Часто задаваемые вопросы

**Q: Почему сумма весов должна быть 1.0?**  
A: Веса представляют вероятностное распределение. Сумма 1.0 означает 100% вероятности.

**Q: Можно ли использовать только некоторые типы логов?**  
A: Да, просто укажите только нужные типы в `log_type_weights` с весами, суммирующимися в 1.0.

**Q: Как генерировать только инциденты?**  
A: Установите `incident_probability: 1.0` и уберите `log_type_weights` или установите их в 0.

**Q: Поддерживается ли IPv6?**  
A: В текущей версии генерируются только IPv4 адреса.

**Q: Как добавить свои пути?**  
A: Просто перечислите их в массиве `forbidden_paths`. Используйте абсолютные пути Unix-систем.

## Дополнительные ресурсы

- [README.md](README.md) - Основная документация модуля
- [examples.py](examples.py) - Примеры использования
- [GitHub loghub](https://github.com/logpai/loghub) - Реальные логи для анализа
