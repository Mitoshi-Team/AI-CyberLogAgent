# ⚡ Шпаргалка по генератору логов

## 🚀 Быстрый старт

```bash
# Режим имитации (1 лог/сек, остановка Ctrl+C)
python -m app_simulation.log_gen.log_gen_cli start imitate attack

# Режим записи для тестов (быстрая генерация)
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable 500
```

## 📋 Все команды

```bash
# Помощь
python -m app_simulation.log_gen.log_gen_cli --help
python -m app_simulation.log_gen.log_gen_cli start --help

# Режим имитации
python -m app_simulation.log_gen.log_gen_cli start imitate <тип>

# Режим записи
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests <тип> [количество]

# Остановка (информация)
python -m app_simulation.log_gen.log_gen_cli stop
```

## 🎨 Типы конфигураций

| Тип | Описание | Error% | Использование |
|-----|----------|--------|---------------|
| `attack` | Симуляция атаки | 30% | Тестирование детекторов взлома |
| `realistic` | Реалистичная смесь | 15% | Общее тестирование, демо |
| `stable` | Стабильная работа | 5% | False positive тесты |
| `load` | Высокая нагрузка | 40% | Нагрузочное тестирование |

## 💡 Примеры использования

```bash
# 1. Генерация 50 логов атаки
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack 50

# 2. Имитация реального сервера
python -m app_simulation.log_gen.log_gen_cli start imitate realistic
# Остановка: Ctrl+C

# 3. Дефолтное количество (500)
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable

# 4. Большой датасет
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests load 10000
```

## 📁 Выходной файл

**Путь:** `app_simulation/log_gen/logs.log`

**Формат:**
```log
# Log generation started: 2025-12-08 18:15:45
# Mode: record_logs_for_tests
# Config: attack
# Total logs: 500

[Mon Dec 08 18:15:48 2025] [error] Security violation...
```

## 🎯 Типичные сценарии

### Разработка детекторов
```bash
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack 5000
python log_manage.py collect_logs
```

### Live демонстрация
```bash
# Терминал 1
python -m app_simulation.log_gen.log_gen_cli start imitate realistic

# Терминал 2
cd log_ai-agent/site && npm run dev
```

### Создание датасета
```bash
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack 2000
mv app_simulation/log_gen/logs.log datasets/attack.log

python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable 2000
mv app_simulation/log_gen/logs.log datasets/stable.log
```

## 🔧 Конфигурации

**Расположение:** `app_simulation/log_gen/configs/`

- `attack.json` - 70% forbidden access
- `realistic_mixed.json` - Сбалансированный микс
- `stable.json` - Минимум ошибок
- `high_load.json` - Ресурсные ошибки

## 📊 Статистика

После генерации показывается:
- ✅ Количество логов
- ⏱️ Время генерации
- 📅 Период логов
- 📈 Распределение по уровням (error, crit, notice, warn)

## 🐛 Частые проблемы

**Цвета не работают в Windows:**
```powershell
$PSStyle.OutputRendering = 'Ansi'
```

**Файл конфига не найден:**
```bash
# Убедитесь что запускаете из корня проекта
pwd  # должно быть .../AI-CyberLogAgent
```

**Прогресс > 100%:**
Это нормально - инциденты генерируют серии логов.

## 📚 Документация

- **Полное руководство:** `LOG_GENERATOR_GUIDE.md`
- **Конфигурации:** `app_simulation/log_gen/CONFIGURATION.md`
- **Старый CLI:** `app_simulation/log_gen/QUICKSTART.md`

---

**Версия:** 2.0 | **Последнее обновление:** 8 декабря 2025
