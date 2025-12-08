# 🆕 Новый генератор логов v2.0

## Что изменилось?

Генератор логов получил **полностью обновленный CLI** с упрощённым интерфейсом и новыми возможностями!

## ⚡ Быстрый старт

### Старый способ (deprecated):
```bash
python -m app_simulation.log_gen.cli --config configs/attack.json --output logs.log -n 100
```

### ✨ Новый способ (v2.0):
```bash
# Быстрая генерация для тестов
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack 100

# Имитация реального сервера (1 лог/сек)
python -m app_simulation.log_gen.log_gen_cli start imitate realistic
```

## 🎯 Основные команды

```bash
# Помощь
python -m app_simulation.log_gen.log_gen_cli --help

# Генерация логов для тестирования
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests <тип> [количество]

# Имитация работы реального сервера
python -m app_simulation.log_gen.log_gen_cli start imitate <тип>

# Остановка (в режиме imitate: Ctrl+C)
python -m app_simulation.log_gen.log_gen_cli stop
```

## 📋 Типы конфигураций

| Тип | Описание |
|-----|----------|
| `attack` | Симуляция атаки на сервер (70% ошибок доступа) |
| `realistic` | Реалистичная смесь всех типов логов |
| `stable` | Стабильная работа с минимумом ошибок |
| `load` | Сервер под высокой нагрузкой |

## 💡 Примеры

```bash
# Генерация 500 атакующих логов (по умолчанию)
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests attack

# Генерация 1000 реалистичных логов
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests realistic 1000

# Имитация реального сервера под атакой
python -m app_simulation.log_gen.log_gen_cli start imitate attack
# Остановка: Ctrl+C
```

## 📁 Выходной файл

Все логи сохраняются в: `app_simulation/log_gen/logs.log`

## 📖 Документация

- **Полное руководство:** [LOG_GENERATOR_GUIDE.md](LOG_GENERATOR_GUIDE.md)
- **Шпаргалка:** [LOG_GEN_CHEATSHEET.md](LOG_GEN_CHEATSHEET.md)
- **Технические детали:** [LOG_GEN_V2_SUMMARY.md](LOG_GEN_V2_SUMMARY.md)

## 🎨 Новые возможности

- ✨ Упрощённый CLI интерфейс
- 🎭 Режим имитации реального сервера (1 лог/сек)
- ⚡ Быстрая генерация для тестов
- 📊 Прогресс-бар и детальная статистика
- 🎨 Цветной вывод в терминале
- 🛡️ Graceful shutdown (Ctrl+C)
- 📝 Дефолтные значения (500 логов)

## ⚠️ Обратная совместимость

Старый CLI (`python -m app_simulation.log_gen.cli`) продолжает работать для обратной совместимости, но рекомендуется использовать новый интерфейс.

---

**Версия:** 2.0  
**Дата:** 8 декабря 2025
