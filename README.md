![Wavescan](./log_ai_agent/site/public/wavescan_logo.svg)

*🌊* [![GitHub release](https://shields.io)](https://github.com/Mitoshi-Team/AI-CyberLogAgent/releases/tag/v13.0.4)

# Wavescan
## Описание

**Wavescan** - интеллектуальная агентная система для анализа логов в области кибербезопасности, предназначенная для выявления угроз, аномалий и инцидентов в автономном режиме.

Система разворачивается локально в инфраструктуре компании, что обеспечивает полный контроль над данными и соответствует требованиям безопасности. Wavescan интегрируется с существующими источниками логов (SIEM, серверы, приложения, сетевые устройства) через Push API или общий том для логов, не требуя кардинальных изменений в текущей архитектуре.

В основе решения лежит комбинация классических методов анализа (YARA, Sigma правила) и современных технологий искусственного интеллекта. Система не просто обнаруживает подозрительные события, а проводит многоуровневый анализ с использованием LLM, сопоставляет инциденты с базой знаний MITRE ATT&CK и формирует структурированные отчёты с объяснениями, уровнем риска и рекомендациями.

Wavescan выступает как "умный помощник" специалиста по информационной безопасности, снижая нагрузку на команду и ускоряя реакцию на инциденты.

> Wavescan — это не просто SIEM, а AI-powered SOC-аналитик, который не только находит угрозы, но и объясняет их, используя многоэтапный анализ и знания MITRE ATT&CK.

### Сравнение с аналогами

| Критерий                        | Wavescan                          | Splunk              | ELK Stack                | Datadog Security Monitoring |
| ------------------------------- | --------------------------------- | ------------------- | ------------------------ | --------------------------- |
| **Тип системы**                 | AI-powered SOC аналитик           | Классический SIEM   | Log management + SIEM    | Cloud SIEM                  |
| **AI-анализ логов**             | ✅ Глубокий (LLM)                  | ⚠️ Ограниченный     | ❌ Нет (в основном rules) | ⚠️ Частично                 |
| **Контекстное понимание**       | ✅ Да (explainable AI)             | ⚠️ Ограничено       | ❌ Нет                    | ⚠️ Частично                 |
| **Двухэтапный AI-пайплайн**     | ✅ Да (LLM → MITRE → LLM)          | ❌ Нет               | ❌ Нет                    | ❌ Нет                       |
| **MITRE ATT&CK интеграция**     | ✅ Автоматическая + в анализе      | ⚠️ Есть, но вручную | ⚠️ Через плагины         | ⚠️ Есть                     |
| **Автоматические отчеты**       | ✅ С объяснениями и рекомендациями | ⚠️ Частично         | ❌ Нет                    | ⚠️ Частично                 |
| **AI-ассистент (чат)**          | ✅ Да                              | ❌ Нет               | ❌ Нет                    | ❌ Нет                       |
| **Скорость внедрения**          | ✅ Быстрая                         | ❌ Долго             | ⚠️ Средняя               | ✅ Быстрая                   |
| **On-Premise**                  | ✅ Да                              | ✅ Да                | ✅ Да                     | ❌ Нет (облако)              |
| **Сложность настройки**         | ✅ Низкая                          | ❌ Высокая           | ❌ Высокая                | ⚠️ Средняя                  |
| **Требования к квалификации**   | ✅ Низкие (за счет AI)             | ❌ Высокие           | ❌ Высокие                | ⚠️ Средние                  |
| **Стоимость внедрения**         | Низкая                             | Высокая               | Средняя                   | Высокая                |

### Преимущества

- **Быстрый старт**: разворачивается за несколько часов и легко интегрируется в существующую инфраструктуру без сложной настройки.
- **Локальная работа**: все данные остаются внутри компании — это критически важно для организаций с высокими требованиями к безопасности.
- **Глубокий контекстный анализ**: LLM не просто фиксирует событие, а объясняет его: что произошло, почему это опасно и какие последствия возможны.
- **Интеграция с MITRE ATT&CK**: автоматическое сопоставление инцидентов с тактиками и техниками атакующих, что упрощает расследование и реагирование.
- **Снижение нагрузки на специалистов**: автоматизация анализа логов и генерации отчетов экономит часы ручной работы.
- **Масштабируемость**: подходит как для небольших команд, так и для крупных инфраструктур с большим потоком логов.
- **Удобный пользовательский интерфейс**: чат с ИИ, фильтрация инцидентов, история отчетов и push-уведомления делают работу комфортной и быстрой.
- **Удобная конфигурация**: возможность добавить/редактировать/удалить yara и sigma правила через веб-интерфейс.

### Функционал

- Автономный анализ логов из внешего источника
- Загрузка логов вручную для анализа
- Диалог с ИИ-ассистентом по кибербезопасности
- Формирование подробных отчетов
- Оценка уровня критичности инцидентов
- Ведение статистики
- Хранение истории отчетов
- Система уведомлений
- Настройка yara и sigma правил

### Пайплайн работы системы

Архитектура анализа построена на **LangGraph** с параллельными ветками обработки:

```mermaid
flowchart TD
    A[Входные логи] --> PF[Prefilter]
    A --> PL[parse_logs]
    PF --> A1[Agent 1 LLM]
    A1 --> A2[Agent 2 RAG]
    PL --> Y[YARA Scan]
    PL --> S[Sigma Scan]
    Y --> A3
    S --> A3
    A2 --> A3[Agent 3 LLM]
    A3 --> R[Финальный отчёт]
```

**Этапы обработки:**

1. **Prefilter** — фильтрация логов для Agent 1 (удаление "мусора" — heartbeat, health check и т.д.)
2. **Параллельный анализ:**
   - **Agent 1 (LLM)** — первичный анализ отфильтрованных логов, выявление аномалий и паттернов
   - **parse_logs** — парсинг всех логов (без фильтрации)
3. **Сканирование (после parse_logs, все логи):**
   - **YARA Scan** — проверка на malware/exploits по YARA-правилам
   - **Sigma Scan** — проверка SIEM-детекций по Sigma-правилам
4. **Agent 2 (RAG)** — поиск MITRE ATT&CK техник для каждого события (если найдены события)
5. **Agent 3 (LLM)** — финальная суммаризация: объединение AI-анализа, YARA, Sigma и MITRE в единый отчёт
6. **Сохранение** — отчёт и метаданные сохраняются в PostgreSQL
7. **Уведомление** — пользователи получают оповещение о новом инциденте

## Начало работы

Клонируем репозиторий

```bash
git clone https://gitverse.ru/mitoshi_team/AI-CyberLogAgent
cd AI-CyberLogAgent
```

### 1. Подготовка модели эмбедингов (для локальной разработки)

Для работы RAG (MITRE ATT&CK) нужна эмбединговая модель `intfloat/multilingual-e5-base` (~1.1 GB).

**Вариант А: Запуск скрипта (рекомендуется)**

```bash
# Из корня репозитория
download_embedding_model.bat        # Windows
```

Скрипт автоматически:
- Проверит HF cache (`~/.cache/huggingface/`) — если модель уже скачана, скопирует оттуда
- Если нет в cache — скачает с HuggingFace (~1-3 минуты)

**Вариант Б: Ручная установка**

```bash
uv run huggingface-cli download intfloat/multilingual-e5-base \
    --local-dir log_ai_agent/ai_agent_v2/embedding/models/multilingual-e5-base
```

**Примечание:**
- Если HuggingFace возвращает `429 Too Many Requests` — подождите 5-15 минут и попробуйте снова
- Модель сохраняется локально и при повторных запусках скачивание не потребуется
- Модель работает в **offline режиме** — никогда не обращается к сети

**Без модели?** Pipeline запустится без RAG (без MITRE ATT&CK контекста). Основной AI-анализ продолжит работать.

---

### Инициализация MITRE ATT&CK

При первом запуске пайплайна:

1. Проверяется существующая ChromaDB (`chroma_db/`)
2. Если пустая — ищется локальный файл `mitre_data/enterprise-attack.json`
3. Если не найден — автоматически скачивается с GitHub:
   - URL: `https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`
   - Сохраняется в `log_ai_agent/ai_agent_v2/mitre_data/enterprise-attack.json`
4. Из STIX JSON извлекаются техники (около 700+ техник)
5. Техники загружаются в ChromaDB с эмбедингами

---

### 2. Развёртывание

1. Создаем файл `.env` в папке `log_ai_agent` на основе `.env.example`

```bash
cd log_ai_agent
cp .env.example .env
```

**Обязательно отредактируйте следующие переменные**:
- `OLLAMA_URL` и `OLLAMA_MODEL` - ваша локальная модель Ollama
- `POSTGRES_PASSWORD` - пароль для базы данных
- `PASSWORD_SALT` - соль для хэширования паролей
- `CLI_TZ_OFFSET_HOURS` - ваш часовой пояс

*Остальное редактировать необязательно*

2. Запускаем Docker

```bash
docker compose up --build -d
```

При первом запуске:
- Скачивается эмбединговая модель `intfloat/multilingual-e5-base` (~1.1 GB) в Docker volume
- Скачивается MITRE ATT&CK STIX JSON с GitHub и сохраняется локально
- Данные сохраняются в Docker volumes

3. Переходим на сайт (порт указывается в `.env`)

```bash
http://localhost:{FRONTEND_PORT}/
```

**Готово!**

Для выключения:

```bash
docker compose down
```

**Примечание:**
- Модель эмбедингов и ChromaDB сохраняются в Docker volumes (`embedding_models`, `chroma_data`)
- MITRE STIX JSON сохраняется в volume `chroma_data` (директория `mitre_data/`)
- При `docker compose restart` скачивание не потребуется. При `docker compose down -v` — данные удаляются.

### Регистрация пользователя

1. Для подключения к консоли пишем (название контейнера указывается в `.env`, команду нужно писать в корневой папке, по умолчанию - `cyberlog-backend`)

```bash
docker exec -it {BACKEND_CONTAINER_NAME} python app.py interactive
```

2. Регистрируем нового пользователя

```bash
register
```

3. Управление правами администратора и просмотр пользователей

```bash
users
set_admin <login> on
set_admin <login> off
```

Раздел **«Конфиг»** в веб-интерфейсе доступен только пользователям с `is_admin = true`.

### Подключение внешнего источника логов (пример: mitre_log_simulator)

Wavescan принимает внешние логи через общий Docker-том (файлы `.log`/`.txt`) или через Push API. Для потоковых источников проще всего писать в общий том — Vector автоматически подхватит файлы из него.

1. В `log_ai_agent/.env` проверьте параметры общего тома и пути:

```bash
PIPELINE_EXTERNAL_LOGS_VOLUME_NAME=cyberlog_external_logs
PIPELINE_EXTERNAL_LOGS_DIR=/app/shared/external
PIPELINE_EXTERNAL_APPEND_FILE=/app/shared/external/external_stream.log
```

2. В `mitre_log_simulator` используйте тот же том (по умолчанию уже совпадает):

```bash
# mitre_log_simulator/.env (необязательно, можно через env)
SHARED_EXTERNAL_LOGS_VOLUME_NAME=cyberlog_external_logs
```

Запуск:

```bash
./run.sh     # Linux/macOS
```

```powershell
.\run.ps1    # Windows
```

Симулятор пишет поток в `/var/log/golden/simulator_stream.log` — этот файл попадает в общий том и автоматически обрабатывается пайплайном.

3. В своей программе:
- смонтируйте тот же Docker-том (например, в `/var/log/golden` или `/data/external`)
- пишите логи в `.log` или `.txt` (append-only), чтобы Vector прочитал их из общего тома

**Альтернатива:** отправляйте логи через Push API: `POST /api/pipeline/logs/upload` или `POST /api/pipeline/logs/text`. Подробности: `log_ai_agent/pipeline/README_INGEST_API.md`.

### Визуализация пайплайна

Для просмотра графа выполнения в реальном времени:

```bash
# Генерация ASCII + Mermaid диаграммы
uv run -m log_ai_agent.ai_agent_v2.visual_graph.render_graph
```

Результат:
- ASCII-граф выводится в консоль
- Mermaid-диаграмма сохраняется в `log_ai_agent/ai_agent_v2/visual_graph/pipeline_graph.mmd`
- Для рендера Mermaid: [mermaid.live](https://mermaid.live) или VS Code расширение

## Интерфейс

Скриншоты интерфейса (находятся в `log_ai_agent/src/`):

![Страница авторизации](./log_ai_agent/src/page1.png)

![Чат с ассистентом](./log_ai_agent/src/page2_1.png)

![Чат с ассистентом](./log_ai_agent/src/page2_2.png)

![История отчетов](./log_ai_agent/src/page3.png)

![Статистика инцидентов](./log_ai_agent/src/page4.png)

![Конфиг](./log_ai_agent/src/page5.png)

## Структура репозитория

```
AI-CyberLogAgent/
├── download_embedding_model.bat      # Скрипт загрузки модели эмбедингов
├── pyproject.toml                    # Конфигурация Python-зависимостей
├── uv.lock                           # Зафиксированные зависимости
├── .dockerignore                     # Исключения для Docker
├── .gitignore                        # Исключения для Git
├── FUNCTIONAL_SPECIFICATION.md       # Функциональные требования
├── README.md                         # Документация
│
└── log_ai_agent/                     # Основной проект
    ├── config/                       # Конфигурация CLI
    │   ├── cfg.py                    # Настройки
    │   └── commands.py                # Команды CLI
    ├── src/                         # Скриншоты интерфейса
    │   ├── page1.png                # Страница авторизации
    │   ├── page2_1.png              # Чат с ассистентом
    │   ├── page2_2.png              # Чат с ассистентом
    │   ├── page3.png                # История отчетов
    │   ├── page4.png                # Статистика инцидентов
    │   └── page5.png                # Конфигурация правил
    │
    ├── ai_agent_v2/                  # AI-агент (LangGraph pipeline)
    │   ├── chains/                   # Цепочки обработки (Agent 1/2/3, RAG)
    │   │   ├── agent1.py             # Первичный анализ логов
    │   │   ├── agent2.py             # Детальный AI-отчёт
    │   │   ├── agent3.py             # Финальная суммаризация
    │   │   ├── graph_nodes.py        # LangGraph узлы
    │   │   ├── rag_chain.py        # RAG MITRE ATT&CK
    │   │   ├── llm.py             # LLM провайдер
    │   │   ├── prefilter.py        # Предобработка логов
    │   │   └── providers/          # LLM провайдеры
    │   │       ├── base.py          # Базовый класс
    │   │       ├── ollama.py      # Ollama провайдер
    │   │       └── gigachat.py     # GigaChat провайдер
    │   ├── engines/                # Сигнатурные движки
    │   │   ├── yara_engine.py    # YARA сканер
    │   │   └── sigma_engine.py   # Sigma сканер
    │   ├── knowledge_base/           # MITRE ATT&CK данные
    │   │   ├── manager.py        # ChromaDB менеджер
    │   │   └── mitre_loader.py # Загрузчик MITRE
    │   ├── models/                # Типы данных
    │   │   └── models_types.py   # Pydantic схемы
    │   ├── parsers/               # Парсеры логов
    │   │   └── apache_parser.py # Apache парсер
    │   ├── pipeline/                 # LangGraph pipeline
    │   │   ├── langgraph_pipeline.py # Основной граф
    │   │   └── __init__.py
    │   ├── prompts/               # Промты для LLM
    │   │   ├── system.py        # Системный промпт
    │   │   └── log_analysis.py # Промпт анализа логов
    │   ├── rules/               # Правила обнаружения
    │   │   ├── yara/         # YARA правила
    │   │   └── sigma/        # Sigma правила
    │   ├── embedding/            # Эмбединговая модель
    │   │   ├── manager.py    # Загрузчик модели
    │   │   └── models/   # Модель (не в Git)
    │   ├── visual_graph/         # Визуализация графа
    │   │   └── render_graph.py # Рендер графа
    │   ├── chroma_db/           # Векторная БД (не в Git)
    │   ├── mitre_data/          # MITRE STIX JSON (скачивается, не в Git)
    │   ├── pipeline_tests/      # Тесты пайплайна
    │   ├── app_integration.py  # Интеграция с FastAPI
    │   ├── callbacks.py      # Колбэки
    │   ├── chat_integration.py # Чат с ИИ
    │   ├── config.py       # Конфигурация агента
    │   ├── init_mitre.py  # Инициализация MITRE
    │   ├── models_types.py # Типы моделей
    │   ├── run.py        # Точка входа
    │   └── README.md    # Документация модуля
    │
    ├── pipeline/                 # Приём и обработка логов
    │   ├── kafka_consumer.py   # Потребитель Kafka
    │   ├── log_ingest_api.py # API загрузки логов
    │   └── README_INGEST_API.md # Документация API
    │
    ├── vector/                 # Vector (сбор логов)
    │   ├── vector.toml      # Конфигурация Vector
    │   └── lua/           # Lua-скрипты
    │
    ├── site/                 # Vue.js фронтенд
    ├── .env                 # Конфигурация (не в Git)
    ├── .env.example         # Пример конфигурации
    ├── app.py              # FastAPI приложение
    ├── docker-compose.yml  # Оркестрация контейнеров
    ├── Dockerfile         # Сборка backend
    ├── docker-entrypoint.sh # Скрипт запуска
└── init-db.sql        # Инициализация БД
```

## Схема БД

### Таблица Users

- user_id: integer (Уникальный идентификатор пользователя, автоинкремент)
- login: text (Логин пользователя)
- password_hash: text (Хэш пароля)
- is_admin: bool (Наличие прав админа)

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

### Таблица UserLogs

- user_log_id: integer (Уникальный идентификатор лога пользователя, автоинкремент)
- user_id: integer (Внешний ключ на Users, пользователь, выполнивший действие)
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
