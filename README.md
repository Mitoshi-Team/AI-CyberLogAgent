# AI Cyber Log Agent

## Описание

**AI Cyber Log Agent** - лёгкая система анализа логов с чат-агентом, комбинирующая правила и AI‑аналитику.

**Преимущества:**
- Быстрый старт: разворачивается за часы, «вписывается» в текущие процессы.
- Снижение шума: комбинированный подход (правила + AI) уменьшает ложные сработки.
- Удобный UX: push‑уведомления, чат, история и фильтры инцидентов.
- Подходит для учебных/пилотных и малых окружений.

**Функционал:**
- Анализ логов
- Общение с ИИ-агентом по кибербезопасности
- Ведение статистики
- История отчетов

## Начало работы

1. Клонируем репозиторий

```bash
git clone https://gitverse.ru/mitoshi_team/AI-CyberLogAgent
```

2. Скачиваем архив по [ссылке](https://drive.google.com/file/d/1QvLBBCINDTVWwq8Opy91MVjqzVOY_TlX/view?usp=sharing) и разархивируем его в `log_ai_agent`

3. Создаем файл `.env` в папке `log_ai_agent` на основе `.env.example` и вносим туда свои переменные для:
- базы данных
- бэкенда
- фронтенда
- GigaChat

4. Переходим в папку
```
cd log_ai_agent
```

5. Запускаем докер

```bash
docker compose up -d
```

6. Переходим на сайт (порт указывается в `.env`)

```bash
http://localhost:{FRONTEND_PORT}/
```

**Готово!**

Для выключения докера пишем

```bash
docker compose down
```

## Регистрация пользователя

1. Для подключения к консоли пишем (название контейнера указывается в `.env`, команду нужно писать в корневой папке)

```bash
docker exec -it {BACKEND_CONTAINER_NAME} python app.py interactive
```

2. Регистрируем нового пользователя
```bash
register
```

## Схема БД

### Таблица Users
- user_id: integer (Уникальный идентификатор пользователя, автоинкремент)
- login: text (Логин пользователя)
- password_hash: text (Хэш пароля)

### Таблица Messages
- message_id: integer (Уникальный идентификатор сообщения, автоинкремент)
- user_id: integer (Внешний ключ на Users, идентификатор пользователя)
- role: text (Роль отправителя сообщения)
- content: text (Содержимое сообщения)
- created_at: timestamp with time zone (Дата и время создания сообщения)

### Таблица ActionTypes
- action_type_id: integer (Уникальный идентификатор типа действия, автоинкремент)
- name: text (Название типа действия)

### Таблица AgentLogs
- agent_log_id: integer (Уникальный идентификатор лога агента, автоинкремент)
- action_type_id: integer (Внешний ключ на ActionTypes, тип действия)
- description: text (Описание действия агента)
- date: timestamp with time zone (Дата и время выполнения действия)

### Таблица Logs
- log_id: integer (Уникальный идентификатор лога, автоинкремент)
- file_content: text (Содержимое файла лога)
- date: timestamp with time zone (Дата и время создания лога)

### Таблица Reports
- report_id: integer (Уникальный идентификатор отчета, автоинкремент)
- description: text (Описание инцидента)
- log_id: integer (Внешний ключ на Logs, связанный лог)
- threat_type_id: integer (Внешний ключ на ThreatTypes, тип угрозы)
- created_at: timestamp with time zone (Дата и время создания отчета)
- severity_level_id (Внешний ключ на SeverityLevels, уровень серьезности)

### Таблица ThreatTypes
- threat_type_id: integer (Уникальный идентификатор типа угрозы, автоинкремент)
- name: text (Название типа угрозы)

### Таблица SeverityLevels
- severity_level_id (Уникальный идентификатор уровня серьезности, автоинкремент)
- name: text (Название уровня серьезности)
