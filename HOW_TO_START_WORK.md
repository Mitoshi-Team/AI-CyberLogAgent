Если проект использует [`uv`](https://github.com/astral-sh/uv) — современный пакетный менеджер и виртуальное окружение от команды, стоящей за Ruff, а в `pyproject.toml` уже указаны зависимости, то запуск проекта для другого разработчика будет быстрым и простым.

---

### ✅ Как запустить проект с помощью `uv`

#### 1. Установите `uv` (если ещё не установлен)

```bash
# С официального сайта (рекомендуется)
pip install uv

# Или через brew (macOS / Linux)
brew install uv

# Или через winget (Windows)
winget install --id=astral.Uv
```

> Официальный сайт: https://docs.astral.sh/uv/

---

#### 2. Клонируйте репозиторий

```bash
git clone https://gitverse.ru/axstiz/AI-CyberLogAgent.git
cd AI-CyberLogAgent
```

---

#### 3. Создайте виртуальное окружение и установите зависимости

```bash
uv sync
```

> Эта команда:
> - Создаст виртуальное окружение (если нет)
> - Установит все зависимости из `[project.dependencies]`
> - Поддержит указанную версию Python (`>=3.13`)

> ⚠️ Убедитесь, что у вас установлен **Python 3.13+**, так как в `pyproject.toml` указано `requires-python = ">=3.13"`

---

#### 4. Запустите проект

Теперь вы можете запускать скрипты проекта:

```bash
uv run python log_manage.py auth
uv run python log_manage.py start_bot
```

или сокращённо:

```bash
uv run log_manage.py start_bot
```

---

### 🧪 Дополнительно: проверка локально

Убедитесь, что код проходит проверку линтером:

```bash
uv run ruff check .
```

**!** Если есть ошибки, исправьте их:

```bash
uv run ruff check --fix
```
***(Но пока некоторые только ручками)***

---


### ✅ Итого: полная инструкция для нового разработчика

```bash
# 1. Установить uv
pip install uv

# 2. Склонировать проект
git clone https://gitverse.ru/axstiz/AI-CyberLogAgent.git
cd AI-CyberLogAgent

# 3. Установить зависимости
uv sync

# 4. Авторизовать Telegram ID
uv run python log_manage.py auth

# 5. Запустить бота
uv run python log_manage.py start_bot
```

---

По вопросам работы со структурой обращаться в тг:
- @Litsummer
- @sser1to