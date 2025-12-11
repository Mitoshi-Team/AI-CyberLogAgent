# 🚀 Быстрый старт - Генератор логов

## Одна команда для начала работы

```bash
# Перейти в директорию проекта
cd AI-CyberLogAgent

# Активировать виртуальное окружение
.venv\Scripts\Activate.ps1  # Windows PowerShell
# или
source .venv/bin/activate    # Linux/Mac

# Сгенерировать реалистичные логи
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --output my_logs.log
```

## 📦 Готовые сценарии

### 1. Реалистичная смесь (рекомендуется для начала)
```bash
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --output analyse_logs.log
```
**Результат:** Сбалансированная смесь всех типов Apache логов

### 2. Симуляция атаки
```bash
python -m log_gen.cli --config log_gen/configs/attack.json --output attack.log -n 100
```
**Результат:** Логи с попытками взлома (70% ошибок доступа к .git, .env, phpmyadmin)

### 3. Нормальная работа сервера
```bash
python -m log_gen.cli --config log_gen/configs/stable.json --output stable.log
```
**Результат:** Стабильный сервер с минимумом ошибок

### 4. Запуск сервера
```bash
python -m log_gen.cli --config log_gen/configs/startup.json --output startup.log
```
**Результат:** Логи инициализации Apache (worker init, child init)

### 5. Просмотр без сохранения
```bash
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --preview -n 30
```
**Результат:** Вывод первых 20 логов в консоль + статистика

## 🎨 Создание своей конфигурации

### Шаг 1: Создать шаблон
```bash
python -m log_gen.cli --create-config my_config.json
```

### Шаг 2: Отредактировать my_config.json

Основные параметры для настройки:

```json
{
  "log_count": 500,
  "log_type_weights": {
    "normal": 0.4,              // 40% - обычные логи
    "error": 0.1,               // 10% - ошибки
    "client_directory_forbidden": 0.2,  // 20% - 403 errors
    "client_file_not_found": 0.1        // 10% - 404 errors
  },
  "client_ip_ranges": ["192.168.0.0/16", "public"],
  "forbidden_paths": ["/admin/", "/config/", "/.git/"]
}
```

### Шаг 3: Использовать
```bash
python -m log_gen.cli --config my_config.json --output custom.log
```

## 📖 Подробная документация

- **log_gen/CONFIGURATION.md** - полное руководство (550+ строк)
- **log_gen/configs/README.md** - описание всех конфигураций
- **log_gen/README.md** - основная документация модуля
- **log_gen/UPDATES.md** - что нового в версии 2.0

## 💡 Полезные команды

```bash
# Показать статистику генерации
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json -n 100 --show-stats --output analyse_logs.log

# Сгенерировать только инциденты определённого типа
python -m log_gen.cli -o incidents.log -n 50 --incident-only memory_leak

# Большой объём логов (10000)
python -m log_gen.cli --config log_gen/configs/high_load.json -n 10000 --output big_dataset.log
```

## ✅ Проверка работы

После установки выполните тест:

```bash
# Быстрый тест (30 логов в консоль)
python -m log_gen.cli --config log_gen/configs/startup.json --preview -n 30
```

Если видите логи в формате:
```
[Thu Dec 04 21:39:55 2025] [notice] jk2_init() Found child 6074 in scoreboard slot 4
[Thu Dec 04 21:39:59 2025] [notice] workerEnv.init() ok /etc/httpd/conf/workers.properties
```

**Всё работает! 🎉**

## 🆘 Проблемы?

### Ошибка: ModuleNotFoundError
```bash
# Убедитесь, что виртуальное окружение активировано
.venv\Scripts\Activate.ps1  # Windows
```

### Ошибка: No module named 'log_gen'
```bash
# Убедитесь, что находитесь в директории AI-CyberLogAgent
cd AI-CyberLogAgent
python -m log_gen.cli --help
```

### Конфигурация не загружается
```bash
# Проверьте путь к конфигурации (относительно текущей директории)
python -m log_gen.cli --config log_gen/configs/realistic_mixed.json --output test.log
```

## 📞 Дополнительная помощь

Подробная документация: `log_gen/CONFIGURATION.md`

Примеры использования в коде: `log_gen/examples.py`
