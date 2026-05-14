"""Prompts for log analysis agents."""

# =============================================================================
# Агент 1: Промпт для первичного анализа
# =============================================================================

PRIMARY_ANALYSIS_USER_PROMPT = """Проанализируй следующий лог-файл на предмет подозрительной активности.

ЛОГ-ФАЙЛ:
```
{log_content}
```

ЗАДАЧА:
1. Выяви все подозрительные активности, ошибки и аномалии
2. Определи временные рамки событий
3. Выдели конкретные строки лога которые указывают на проблемы
4. Сгруппируй похожие события
5. Опиши что произошло в каждом случае
6. Определи ВЗАИМОСВЯЗИ между событиями

ФОРМАТ ОТВЕТА:
## Обнаруженные события

### Событие 1: [название]
- **Время**: [timestamp если есть]
- **Описание**: что произошло
- **Индикаторы**: конкретные строки из лога
- **Признаки**: почему это подозрительно

### Событие 2: [название]
...

## Итог
Краткое резюме всех обнаруженных подозрительных активностей."""

PRIMARY_ANALYSIS_USER_PROMPT_V2 = """Analyze the following log file for suspicious activity. Output ONLY in English.

LOG FILE:
```
{log_content}
```

TASK:
1. Identify all suspicious activities, errors, and anomalies
2. Determine timeframes of events (timestamp)
3. Extract specific log lines that indicate problems
4. GROUP related events
5. Describe what happened in each case
6. Identify RELATIONSHIPS between events

IMPORTANT: EVENT GROUPING
- Group events by possible connection: user, IP, attack_pattern, service, destination, request_path etc.
- DO NOT group by timestamp! This is forbidden as logs already come in 5-minute intervals.
- One event (log line) CAN be in multiple groups if it may be related to different activities.
- If an event is suspicious but not connected to others - create a single-element group.

OUTPUT:
1. **Primary analysis** - full report with event descriptions and relationships
2. **Brief summary** - 2-3 sentences for quick understanding
3. **Event groups** - for MITRE ATT&CK lookup

RESPONSE FORMAT:
## Primary Analysis

[Full structured analysis of all events and their relationships]

## Brief Summary

[2-3 sentences summarizing the situation]

## Event Groups for MITRE

For each group provide:
- **group_id**: unique group identifier (g1, g2, ...)
- **events**: list of events in the group (each with description, timestamp, log_line)
- **first_seen**: time of first event in group
- **last_seen**: time of last event in group
- **keywords**: list of keywords for RAG search (5-10 terms in English, including: attack type, tools, techniques, indicators, commands, file/process names, vulnerabilities, etc.)
- **description**: DETAILED English description in style "Detected...", "Observed..." (minimum 100 characters). Description should include:
  - Nature of threat (brute force, SQL injection, etc.)
  - Key indicators (IP, user, path, ports, etc.)
  - Context and scope of activity
  - Potential consequences

---GROUPS---
[
  {{
    "group_id": "g1",
    "events": [
      {{
        "description": "Event description",
        "timestamp": "2025-12-17 13:06:06",
        "log_line": "[Wed Dec 17 13:06:06 2025] [error] [client 89.23.74.19] Authentication failed..."
      }}
    ],
    "first_seen": "2025-12-17 13:06:06",
    "last_seen": "2025-12-17 13:06:06",
    "keywords": ["SSH brute force", "authentication failure", "89.23.74.19", "admin", "failed login"],
    "description": "Detected a series of failed SSH authentication attempts for user admin from IP 89.23.74.19. Observed 15 login attempts with various passwords indicating a brute force attack. Source IP belongs to suspicious range, recommend blocking and checking logs for successful login."
  }},
  {{
    "group_id": "g2",
    "events": [...],
    "first_seen": "...",
    "last_seen": "...",
    "keywords": [...],
    "description": "..."
  }}
]
---GROUPS---

IMPORTANT:
- Section ---GROUPS--- should contain ONLY suspicious groups.
- If no events - write empty array [].
- If an event can belong to multiple groups - include it in all relevant groups.
- Descriptions must be DETAILED and informative (minimum 100 characters).
- Keywords should include terms for MITRE ATT&CK knowledge base search.
- Better to over-detect than miss, but do not add events "just in case"."""

# =============================================================================
# Агент 2: Промпт для финального отчёта
# =============================================================================

FINAL_REPORT_USER_PROMPT = """На основе первичного анализа логов и данных из MITRE ATT&CK сформируй итоговый отчёт.

ПЕРВИЧНЫЙ АНАЛИЗ:
{primary_analysis}

МИНИ-ОТЧЕТ ОТ АГЕНТА 1:
{mini_report}

НАЙДЕННЫЕ MITRE ТЕХНИКИ (для каждого события):
{mitre_techniques_str}

ЗАДАЧА:
1. Определи тип угрозы (threat_type_id: 1-11)
2. Оцени уровень серьёзности (severity_level_id: 1-4)
3. Сопоставь обнаруженные активности с техниками MITRE ATT&CK
4. Сформируй подробный отчёт
5. Дай практические рекомендации по устранению

ФОРМАТ ОТВЕТА:
## Отчёт об инциденте безопасности

### Описание инцидента
Подробное описание того что произошло.

### Сопоставление с MITRE ATT&CK
- **Тактика**: [название]
- **Техники**: [ID и название]
- **Линия защиты**: [1/2/3]

### Уровень серьёзности
[Обоснование выбора severity]

### Тип угрозы
[Обоснование выбора threat_type]

### Рекомендации
- [Конкретные шаги по устранению]
- [Меры по предотвращению]

---META---
severity_level_id: <число 1-4>
threat_type_id: <число 1-11>
mitre_techniques: ["<ID техники>", ...]
---END---"""

# =============================================================================
# Агент 3: Промпт для финальной суммаризации
# =============================================================================

SUMMARIZER_USER_PROMPT = """Объедини все результаты проверок в единый отчёт.

=== ВНИМАНИЕ ===
Часть событий от Agent 1 могут быть ложными срабатываниями (галлюцинации).
Проверь каждое событие:
- [YES] Есть в YARA/Sigma/MITRE? -> подтверждено -> включай в отчёт
- [NO] Нет нигде? -> НЕПОДТВЕРЖДЕНО -> вынеси в блок "требует проверки"

=== ПЕРВИЧНЫЙ АНАЛИЗ (Agent 1) ===
Событий обнаружено: {events_found}

{mini_report}

{primary_analysis}

=== MITRE ATT&CK (Agent 2 - через RAG) ===
{mitre_context}

=== ОТЧЕТ AI (Agent 2) ===
Оценка серьёзности: {severity_level_id}/4
Тип угрозы: {threat_type_id}/11
Техники MITRE: {mitre_techniques_str}

{agent2_report}

=== YARA SCAN ===
Совпадений: {yara_count}
{yara_context}

=== SIGMA SCAN ===
Совпадений: {sigma_count}
{sigma_context}

ЗАДАЧА:
1. Опиши инцидент, объединяя все источники
2. Покажи как YARA/Sigma совпадения подтверждают выводы AI
3. Сопоставь с техниками MITRE ATT&CK
4. Дай рекомендации по устранению и предотвращению
5. Сохрани/обоснуй оценку серьёзности и типа угрозы
6. НЕПОДТВЕРЖДЕННЫЕ события вынеси в отдельный блок (не влияют на severity!)

ФОРМАТ ОТВЕТА:
## Отчёт об инциденте безопасности

### Описание инцидента
Подробное описание того что произошло.

### Результаты проверки YARA
Результаты совпадений с YARA-правилами.

### Результаты проверки Sigma
Результаты совпадений с Sigma-правилами.

### Сопоставление с MITRE ATT&CK
- **Тактика**: [название]
- **Техники**: [ID и название]

### Уровень серьёзности
[Обоснование]

### Тип угрозы
[Обоснование]

### Рекомендации
- [Конкретные шаги по устранению]
- [Меры по предотвращению]

### ❗ События, требующие ручной проверки❗

[краткое описание события] (timestamp: ...)
[оригинальная строка из лога]
ВНИМАНИЕ: Это могут быть ложные срабатывания Agent 1

---META---
severity_level_id: <число 1-4>
threat_type_id: <число 1-11>
mitre_techniques: ["<ID техники>", ...]
yara_rules: ["<имя правила>", ...]
sigma_rules: ["<имя правила>", ...]
events_found: <число>
confidence_level: "high" | "medium" | "low"
unconfirmed_events_count: <число>
---END---"""
