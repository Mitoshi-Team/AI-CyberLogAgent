# MITRE Log Simulator Container

Автономный контейнер-симулятор для потоковой генерации шумных логов и безопасной имитации MITRE ATT&CK техник.

## Что делает

- Генерирует шумовой поток логов в stdout:
  - nginx access + error
  - postgres connection + query
  - syslog auth + cron + kernel
  - app-логи в JSON (INFO/WARN/ERROR)
- Периодически инжектит безопасные симуляции техник MITRE ATT&CK (10 техник).
- После каждой атаки выполняет cleanup и пишет статус в stdout.
- Ведет golden-журнал на volume хоста в файле /var/log/golden/attack_timeline.log.
- Ведет единый append-only файл потока логов: /var/log/golden/simulator_stream.log.
- Поддерживает детерминизм через RANDOM_SEED.

## Структура

- Dockerfile
- orchestrator.sh
- docker-compose.yml
- run.sh
- run.ps1
- golden_logs/

## Переменные окружения

| Переменная | По умолчанию | Описание |
|---|---:|---|
| ATTACK_MODE | random | Режим атак: random или fixed |
| FIXED_TECHNIQUE | T1059 | Техника для fixed-режима |
| ATTACK_INTERVAL | 90 | Интервал в сек для fixed-режима |
| ATTACK_INTERVAL_MIN | 60 | Нижняя граница интервала random |
| ATTACK_INTERVAL_MAX | 120 | Верхняя граница интервала random |
| LOG_RATE | 200 | Базовая интенсивность логов, записей/сек (фактически ±10%) |
| FLOG_RPS | 5 | Вклад фонового flog в общий поток (для точного rate-бюджета) |
| MAX_LOG_LINES | 0 | Остановить симулятор после N строк логов (0 = без лимита) |
| RANDOM_SEED | 42 | Seed для детерминированной последовательности |
| HOSTNAME_OVERRIDE | target-node-01 | Имя узла в логах |

## Поддерживаемые техники (безопасная симуляция)

- T1059
- T1003
- T1547
- T1053
- T1136
- T1027
- T1082
- T1046
- T1070
- T1566

## Быстрый запуск

### 1) Одна команда (рекомендуется)

```bash
chmod +x run.sh orchestrator.sh
./run.sh
```

Windows PowerShell:

```powershell
.\run.ps1
```

Примеры удобного запуска:

```bash
# старт (случайные атаки)
./run.sh start

# fixed режим: одна техника каждые 60 сек
./run.sh fixed T1059 60

# random режим: интервал 30-45 сек, seed=123, без пересборки
./run.sh --random --min 30 --max 45 --seed 123 --no-build

# короткий smoke-тест: 250 логов и автоматическое завершение
./run.sh fixed T1059 5 --max-logs 250

# посмотреть логи
./run.sh logs

# остановить контейнер
./run.sh stop
```

```powershell
# старт (случайные атаки)
.\run.ps1 start

# fixed режим: одна техника каждые 60 сек
.\run.ps1 fixed T1059 60

# random режим: интервал 30-45 сек, seed=123, без пересборки
.\run.ps1 random -MinInterval 30 -MaxInterval 45 -Seed 123 -NoBuild

# короткий smoke-тест: 250 логов и автоматическое завершение
.\run.ps1 fixed T1059 5 -MaxLogs 250

# посмотреть логи
.\run.ps1 logs

# остановить контейнер
.\run.ps1 stop
```

### 2) Случайные атаки (docker run)

```bash
docker build -t my_image .
docker run --rm -v ./golden_logs:/var/log/golden my_image
```

Для авто-перезапуска при падении лучше использовать:

```bash
docker run --restart unless-stopped -v ./golden_logs:/var/log/golden my_image
```

### 3) Фиксированная техника T1059 каждые 60 секунд

```bash
docker run --rm \
  -e ATTACK_MODE=fixed \
  -e FIXED_TECHNIQUE=T1059 \
  -e ATTACK_INTERVAL=60 \
  -v ./golden_logs:/var/log/golden \
  my_image
```

### 4) Детерминированный seed

```bash
docker run --rm -e RANDOM_SEED=123 -v ./golden_logs:/var/log/golden my_image
```

## Формат логов

- Общий поток: mixed plain text
- app-лог: JSON

Примеры:

```text
2025-04-03T10:00:01Z app {"user":"admin","action":"login","status":200}
2025-04-03T10:00:02Z nginx_access 192.168.1.7 - - "GET /api/v1/items/42 HTTP/1.1" 200 512
2025-04-03T10:00:03Z [TEST_START] Running T1003
2025-04-03T10:00:04Z [T1003] Simulated execution: read fake credential material from /tmp/fake_credential_dump_...txt marker=/tmp/attack_T1003_...
2025-04-03T10:00:05Z [CLEANUP_OK] All simulated artifacts removed
```

## Golden log

Файл: /var/log/golden/attack_timeline.log

Потоковый лог:

```text
/var/log/golden/simulator_stream.log
```

Формат строки:

```text
TIMESTAMP|TECHNIQUE|START|END|CLEANUP_STATUS
```

Пример:

```text
2026-04-03T12:35:00Z|T1059|2026-04-03T12:34:59Z|2026-04-03T12:35:00Z|CLEANUP_OK
```

## Healthcheck

Контейнер считается healthy, если:

- жив процесс orchestrator.sh
- есть минимум одна запись в stdout за последние 60 секунд
- нет флага /tmp/unhealthy

Параметры:

- interval=30s
- timeout=10s
- retries=3

## Сценарии проверки

### Проверка меток атак

```bash
docker logs -f mitre-log-simulator | grep "TEST_START\|TEST_END\|CLEANUP_"
```

### Проверка golden-журнала

```bash
tail -f ./golden_logs/attack_timeline.log
```

### Проверка health

```bash
docker inspect --format='{{json .State.Health}}' mitre-log-simulator
```

## Ограничения безопасности

- Только симуляция поведения и лог-следов.
- Никаких реальных деструктивных действий.
- Никаких изменений системных файлов вне /tmp.
- Для T1046 выполняются только локальные эхо-пробы 127.0.0.1.
