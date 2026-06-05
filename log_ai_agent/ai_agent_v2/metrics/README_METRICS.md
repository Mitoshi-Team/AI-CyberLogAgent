# Detection Quality Metrics

> **Актуальные метрики:** `TESTS_DATA/test2/REPORT_2.md` (полный отчёт),
> `TESTS_DATA/SUMMARY_REPORT.md` (сводка).
> Тест test2 — единственный верифицированный (43 мин, ~850 строк).


Автоматическая оценка качества детектирования MITRE ATT&CK техник.

## Как это работает

```
mitre-log-simulator                 log_ai_agent (pipeline)
┌─────────────────────┐            ┌──────────────────────────┐
│  generator.py       │            │  langgraph_pipeline.py   │
│  ─────────────────  │            │  ─────────────────────── │
│  noise + attack     │  ──────►   │  анализ логов            │
│  logs               │  volume    │                          │
│                     │            │  после каждого запуска   │
│  attack_timeline.log│            │  пишет pipeline_metrics  │
│  (ground truth)     │            │  .log                    │
└─────────────────────┘            └──────────────────────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │  evaluate.py     │
                                  │  сравнивает      │
                                  │  truth vs detect │
                                  │  TP / FP / FN    │
                                  │  Precision/Recall│
                                  │  / F1            │
                                  └──────────────────┘
```

### Два источника данных

1. **Ground truth** — `attack_timeline.log` от `mitre-log-simulator`:
   - Формат: `{start_iso}|{end_iso}|{technique_id}` (одна строка на атаку)
   - Лежит в общем volume `cyberlog_external_logs` → `/app/shared/external/`

2. **Pipeline detections** — `pipeline_metrics.log`:
   - Формат:
     ```
     2026-05-26T13:05:00Z - INCIDENT
     -----------------
     timestamp_start: ...
     timestamp_end: ...
     RAG: T1110, T1496
     YARA: Path_Traversal_Advanced
     SIGMA: Нет
     -----------------
     ```
   - Пишется после каждого успешного анализа, если найдены события
   - Лежит в `ai_agent_v2/metrics/pipeline_metrics.log`

### Метрики

- **True Positive**: атака была смоделирована И детектирована RAG
- **False Positive**: детектировано RAG, но атака не проводилась
- **False Negative**: атака проводилась, но RAG не детектировал
- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **F1-score** = 2 × (P × R) / (P + R)

## Использование

### 1. Запуск пайплайна

Анализ работает как обычно — через загрузку файла (API) или через Vector push.
После каждого успешного анализа metrics_logger сам допишет блок в `pipeline_metrics.log`.

### 2. Оценка качества

```bash
# Внутри контейнера backend:
docker exec cyberlog-backend python -m ai_agent_v2.metrics.evaluate

# С кастомными путями:
docker exec cyberlog-backend python -m ai_agent_v2.metrics.evaluate \
    --ground-truth /app/shared/external/attack_timeline.log \
    --detections /app/log_ai_agent/ai_agent_v2/metrics/pipeline_metrics.log
```

### 3. Пример вывода

```
==================================================
  DETECTION QUALITY REPORT
==================================================
  True Positives  (3):  T1059, T1110, T1496
  False Positives (1):  T1003
  False Negatives (1):  T1027

  Precision: 75.00%
  Recall:    75.00%
  F1-score:  75.00%
==================================================
```

## Автономный прогон (1-2 часа)

1. Запустить симулятор атак:
   ```bash
   cd mitre_log_simulator
   docker-compose up -d
   ```

2. Убедиться, что Vector подхватывает логи и шлёт в pipeline.

3. После завершения теста — запустить evaluation:
   ```bash
   docker exec cyberlog-backend python -m ai_agent_v2.metrics.evaluate
   ```

4. Просмотреть сырые данные:
   ```bash
   # Ground truth:
   cat /app/shared/external/attack_timeline.log

   # Pipeline detections:
   cat /app/log_ai_agent/ai_agent_v2/metrics/pipeline_metrics.log
   ```

## Файлы модуля

| Файл | Назначение |
|------|-----------|
| `__init__.py` | Пакет |
| `metrics_logger.py` | Пишет `pipeline_metrics.log` после каждого анализа |
| `evaluate.py` | Сравнивает ground truth и pipeline detections |
| `pipeline_metrics.log` | Журнал детекций (создаётся автоматически) |
| `README_METRICS.md` | Этот файл |
