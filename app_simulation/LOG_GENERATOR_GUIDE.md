# 🚀 Руководство по использованию генератора логов

## Обзор

Новый CLI для генератора логов предоставляет два режима работы:
- **`imitate`** - имитация реального сервера с генерацией 1 лог/секунду
- **`record_logs_for_tests`** - быстрая генерация файла с логами для тестирования

## 📋 Синтаксис команд

### Базовая структура

```bash
python -m app_simulation.log_gen.log_gen_cli start <режим> <тип_конфигурации> [количество_логов]
python -m app_simulation.log_gen.log_gen_cli stop
```

### Параметры

| Параметр | Обязательный | Описание | Значения |
|----------|--------------|----------|----------|
| `<режим>` | ✅ Да | Режим работы генератора | `imitate`, `record_logs_for_tests` |
| `<тип_конфигурации>` | ✅ Да | Тип сценария генерации | `attack`, `realistic`, `stable`, `load` |
| `[количество_логов]` | ❌ Нет | Количество генерируемых логов | Число (по умолчанию: 500) |

---

## 🎭 Режимы работы

### 1️⃣ Режим `imitate` - Имитация реального сервера

**Назначение:** Непрерывная генерация логов в реальном времени для симуляции работающего сервера.

**Характеристики:**
- ⏱️ Генерация: **1 лог/секунду**
- 🕐 Timestamp: **Реальное время**
- 🔄 Длительность: **До остановки (Ctrl+C)**
- 💾 Файл: `app_simulation/log_gen/logs.log`

**Примеры использования:**

```bash
# Симуляция атаки на сервер
python -m app_simulation.log_gen.log_gen_cli start imitate attack

# Реалистичная работа сервера
python -m app_simulation.log_gen.log_gen_cli start imitate realistic

# Стабильный сервер без нагрузки
python -m app_simulation.log_gen.log_gen_cli start imitate stable

# Сервер под высокой нагрузкой
python -m app_simulation.log_gen.log_gen_cli start imitate load
```

**Вывод в консоль:**
```
🚀 Запуск режима имитации
  Конфигурация: attack
  Config файл: app_simulation\log_gen\configs\attack.json
  Скорость: 1 лог/секунду
  Выходной файл: C:\...\app_simulation\log_gen\logs.log

Нажмите Ctrl+C для остановки

[00001] [Mon Dec 08 18:15:48 2025] [error] Security violation: unauthorized access
[00002] [Mon Dec 08 18:15:49 2025] [crit] Server reached MaxClients setting
[00003] [Mon Dec 08 18:15:50 2025] [error] Permission denied: user 'guest'
...
```

**Остановка:**
```bash
# Нажмите Ctrl+C в терминале где запущен генератор
# Автоматически выведется статистика:

🛑 Получен сигнал остановки...

📊 Статистика генерации:
  Сгенерировано логов: 123
  Время работы: 0:02:03
  Файл: C:\...\app_simulation\log_gen\logs.log
```

---

### 2️⃣ Режим `record_logs_for_tests` - Быстрая генерация для тестов

**Назначение:** Моментальная генерация определённого количества логов для тестирования системы анализа.

**Характеристики:**
- ⚡ Генерация: **Максимально быстро**
- 🕐 Timestamp: **Инкрементные (симуляция времени)**
- 📊 Прогресс-бар: **Да**
- 💾 Файл: `app_simulation/log_gen/logs.log`

**Примеры использования:**

```bash
# Генерация 500 логов (по умолчанию)
python log_gen.py start record_logs_for_tests attack

# Генерация 1000 логов атаки
python log_gen.py start record_logs_for_tests attack 1000

# Генерация 50 логов стабильной работы
python log_gen.py start record_logs_for_tests stable 50

# Генерация 5000 логов для нагрузочного тестирования
python log_gen.py start record_logs_for_tests load 5000
```

**Вывод в консоль:**
```
📝 Режим записи логов для тестирования
  Конфигурация: attack
  Config файл: app_simulation\log_gen\configs\attack.json
  Количество логов: 500
  Выходной файл: C:\...\app_simulation\log_gen\logs.log

🔄 Генерация логов...

Прогресс: |████████████████████████████| 500/500 (100.0%)

📊 Статистика генерации:
  Конфигурация: attack
  Всего записей: 500
  Время генерации: 0:00:00.007867
  Период логов: 2025-12-08 18:18:20 - 2025-12-08 18:18:50
  Длительность логов: 0:00:30

  Распределение по уровням:
    error   :   340 ( 66.9%)
    crit    :   160 ( 31.5%)
    notice  :     8 (  1.6%)

✅ Логи успешно сгенерированы!
💾 Сохранено в: C:\...\app_simulation\log_gen\logs.log
```

---

## 🎨 Типы конфигураций

### `attack` - Симуляция атаки

**Описание:** Логи с высокой концентрацией ошибок доступа и попыток взлома.

**Характеристики:**
- ❌ Error probability: **30%**
- 🚨 Incident probability: **20%**
- 🎯 Forbidden paths: `/admin/`, `/.git/`, `/etc/passwd`, `/root/.ssh/`, `.env`

**Типичные логи:**
```log
[error] [client 103.127.44.60] Directory index forbidden by rule: /etc/passwd
[crit] Server reached MaxClients setting, refusing new connections
[error] Security violation: unauthorized access attempt to /admin
[error] Permission denied: user 'guest' cannot access /etc/passwd
```

**Использование:**
```bash
python log_gen.py start imitate attack
python log_gen.py start record_logs_for_tests attack 1000
```

---

### `realistic` - Реалистичная смесь

**Описание:** Сбалансированная смесь всех типов логов как на реальном сервере.

**Характеристики:**
- ✅ Error probability: **15%**
- 📊 Разнообразие: Все типы логов (mod_jk, client errors, system notices)
- 🌐 IP ranges: Public + private networks

**Типичные логи:**
```log
[notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[notice] jk2_init() Found child 6234 in scoreboard slot 3
[error] mod_jk child workerEnv in error state 5
[error] [client 192.168.1.45] File does not exist: /var/www/html/favicon.ico
[notice] Apache/2.2.3 configured -- resuming normal operations
```

**Использование:**
```bash
python log_gen.py start imitate realistic
python log_gen.py start record_logs_for_tests realistic 500
```

---

### `stable` - Стабильная работа

**Описание:** Минимум ошибок, стабильная работа сервера.

**Характеристики:**
- ✅ Error probability: **5%**
- 🚨 Incident probability: **2%**
- 🕐 Time increment: 10-60 секунд

**Типичные логи:**
```log
[notice] workerEnv.init() ok /etc/httpd/conf/workers2.properties
[notice] jk2_init() Found child 6120 in scoreboard slot 5
[notice] Apache/2.2.3 configured -- resuming normal operations
[notice] Server built: Dec  8 2025 15:30:45
[error] mod_jk child workerEnv in error state 2  # редко
```

**Использование:**
```bash
python log_gen.py start imitate stable
python log_gen.py start record_logs_for_tests stable 200
```

---

### `load` - Высокая нагрузка

**Описание:** Сервер под высокой нагрузкой с частыми ошибками ресурсов.

**Характеристики:**
- ❌ Error probability: **40%**
- 🚨 Incident types: Resource exhaustion, memory leaks, connection failures
- ⚡ Time increment: 1-5 секунд (быстрая генерация событий)

**Типичные логи:**
```log
[crit] Server reached MaxClients setting, refusing new connections
[error] Memory allocation failed for worker 6789
[crit] File descriptor limit reached, cannot accept connections
[error] Connection to backend server failed after 3 attempts
[crit] Thread pool exhausted, queuing requests
```

**Использование:**
```bash
python log_gen.py start imitate load
python log_gen.py start record_logs_for_tests load 2000
```

---

## 📊 Структура выходного файла

Файл `app_simulation/log_gen/logs.log` имеет следующую структуру:

```log
# Log generation started: 2025-12-08 18:15:45.007827
# Mode: record_logs_for_tests
# Config: attack
# Total logs: 500

[Mon Dec 08 18:15:48 2025] [error] Security violation: unauthorized access
[Mon Dec 08 18:15:51 2025] [error] Permission denied: user 'guest'
...
```

**Метаданные (комментарии в начале):**
- Время начала генерации
- Режим (imitate/record_logs_for_tests)
- Тип конфигурации
- Ожидаемое количество логов (для record_logs_for_tests)

**Формат логов:**
```
[День Месяц Число ЧЧ:ММ:СС Год] [уровень] сообщение
```
