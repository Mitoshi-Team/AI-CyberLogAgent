# Ingest API для внешних логов

Этот документ описывает API, через который внешний источник может передавать логи в общий Docker-том проекта.

## Назначение

API принимает логи и дописывает их в единый append-only файл (по умолчанию `/app/shared/external/external_stream.log`).
Далее их автоматически подхватывает Vector, обрабатывает и отправляет в Kafka.

Цепочка:
1. Внешний источник -> Ingest API (backend)
2. Ingest API -> общий том (`PIPELINE_EXTERNAL_LOGS_DIR`)
3. Vector -> Kafka
4. Kafka -> backend consumer
5. backend consumer -> анализ через LLM -> запись в `Logs` и `Reports`

Важно: анализ выполняется асинхронно после загрузки файла. API загрузки возвращает успешное добавление строк,
а сам отчет появляется в базе немного позже (обычно от нескольких секунд до минут, в зависимости от нагрузки).

## Эндпоинты

### 1) Загрузка файла

`POST /api/pipeline/logs/upload`

Формат: `multipart/form-data`

Поля формы:
- `file` (обязательно): файл логов
- `source` (необязательно): имя внешнего источника, по умолчанию `external`

Пример `curl`:

```bash
curl -X POST "http://localhost:8000/api/pipeline/logs/upload" \
  -F "source=partner-system" \
  -F "file=@./sample.log"
```

Пример ответа:

```json
{
  "success": true,
  "message": "Лог добавлен в общий поток внешних логов",
  "path": "/app/shared/external/external_stream.log",
  "size_bytes": 24812
}
```

### 2) Отправка логов текстом

`POST /api/pipeline/logs/text`

Формат: `application/json`

Тело запроса:
- `content` (обязательно): текст логов
- `filename` (необязательно): имя файла, по умолчанию `payload.log`
- `source` (необязательно): имя внешнего источника, по умолчанию `external`

Пример `curl`:

```bash
curl -X POST "http://localhost:8000/api/pipeline/logs/text" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"ERROR: auth failed\\nWARN: retry\",\"filename\":\"auth.log\",\"source\":\"siem-gateway\"}"
```
