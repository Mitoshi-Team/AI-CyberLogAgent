# 📦 Обновление: Файл генератора перенесён

## Что изменилось?

CLI генератора логов (`log_gen_cli.py`) теперь находится в директории `app_simulation/log_gen/` вместо корня проекта.

## Новое расположение

**Файл:** `app_simulation/log_gen/log_gen_cli.py`

## Как использовать?

### До (старый путь):
```bash
python log_gen.py start imitate attack
```

### Сейчас (новый путь):
```bash
python -m app_simulation.log_gen.log_gen_cli start imitate attack
```

## Примеры команд

```bash
# Помощь
python -m app_simulation.log_gen.log_gen_cli --help

# Режим имитации
python -m app_simulation.log_gen.log_gen_cli start imitate attack

# Режим записи
python -m app_simulation.log_gen.log_gen_cli start record_logs_for_tests stable 500
```

## Зачем изменили?

- ✅ Логичная структура: CLI находится рядом с модулем генератора
- ✅ Соответствие Python best practices
- ✅ Относительные импорты работают корректно
- ✅ Лучшая организация кода проекта

## Совместимость

Старый CLI (`python -m app_simulation.log_gen.cli`) продолжает работать для обратной совместимости.

## Документация обновлена

Все файлы документации обновлены с новым путём:
- ✅ `LOG_GENERATOR_GUIDE.md`
- ✅ `LOG_GEN_CHEATSHEET.md`
- ✅ `NEW_LOG_GENERATOR.md`

---

**Дата обновления:** 8 декабря 2025
