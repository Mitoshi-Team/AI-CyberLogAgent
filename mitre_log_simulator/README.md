# MITRE Log Simulator

Этот каталог содержит отдельный Docker-симулятор для генерации логов в двух слоях:

1. Фоновый шум на базе Flog в одном веб-формате.
2. Слой атак Atomic Red Team через локальную копию `atomic-red-team` и PowerShell Core.

Симулятор пишет данные одновременно в stdout контейнера и в файловый лог внутри внешнего volume. Дополнительно ведётся файл меток атак в формате CSV:

- `timestamp_start`
- `timestamp_end`
- `technique`

## Что создается

Внутри volume `shared_external_logs` будут появляться:

- `attack_timeline.log` — таймлайн атак в формате `timestamp_start|timestamp_end|technique`
- `generated_logs.log` — все сгенерированные логи и вывод атак
- `attack_markers.csv` — временные метки атак для сопоставления с анализом

Volume по умолчанию:

- `cyberlog_external_logs`

## Требования

- Docker Desktop или Docker Engine с поддержкой `docker compose`
- PowerShell 7 на хосте для запуска `run.ps1`
- Доступ в интернет на этапе сборки образа, чтобы установить PowerShell-модуль Atomic Red Team и скачать `atomic-red-team`

## Запуск

Базовый старт без атак:

```powershell
.\run.ps1 start -NoAttacks
```

Одна конкретная техника:

```powershell
.\run.ps1 start -Technique T1059 -IntervalSeconds 10
```

Рандомные атаки:

```powershell
.\run.ps1 start -RandomAttacks -IntervalSeconds 15
```

Остановка:

```powershell
.\run.ps1 stop
```

Просмотр логов отдельно:

```powershell
.\run.ps1 logs
```

## Флаги `start`

- `-Technique <T####>` — запуск одной конкретной атаки Atomic Red Team.
- `-RandomAttacks` — случайный выбор техники на каждом цикле.
- `-NoAttacks` — только фоновые логи, без атак.
- `-IntervalSeconds <N>` — пауза между циклами генерации и атаками; если не указать, выбирается случайно от 10 до 30 секунд.
- `-NoiseBatchSize <N>` — размер пакета фоновых логов за цикл; если не указать, выбирается случайно от 30 до 100.
- `-Detached` — запуск контейнера в фоне.

Только один режим атак может быть активен одновременно: `-Technique`, `-RandomAttacks` или `-NoAttacks`.

## Как это работает

Контейнер собран на полном Ubuntu-образе, а не на slim-версии, чтобы внутри были стандартные утилиты, полезные для имитации поведения атакующего:

- `tar`
- `base64`
- `nc`
- `curl`
- `git`

Внутри образа установлены:

- PowerShell Core
- Flog
- `Invoke-AtomicRedTeam`
- локальная копия `redcanaryco/atomic-red-team` с atomics

## Volume / папка логов на хосте

По умолчанию `run.ps1 start` создаёт в корне проекта папку `shared_external_logs` и монтирует её в контейнер как bind-mount. В этой папке вы увидите те же файлы, что и в внутреннем каталоге контейнера:

- `attack_timeline.log` — таймлайн атак в формате `timestamp_start|timestamp_end|technique`
- `generated_logs.log` — все сгенерированные логи и вывод атак
- `attack_markers.csv` — временные метки атак для сопоставления с анализом

Если вы предпочитаете использовать именованный Docker volume вместо папки на хосте, установите переменную окружения `SHARED_EXTERNAL_LOGS_BIND` в значение `shared_external_logs` перед запуском — тогда будет использован именованный volume `cyberlog_external_logs`:

```yaml
shared_external_logs:
  external: true
  name: ${SHARED_EXTERNAL_LOGS_VOLUME_NAME:-cyberlog_external_logs}
```

Формат `attack_timeline.log` умышленно сокращён до трёх полей, без дублирования времени старта атаки и без статуса cleanup.

## Примечания

- Если выбранная техника не поддерживается на Linux, Atomic Red Team может пропустить тест или вывести ошибку, но генератор продолжит работу.
- По умолчанию контейнер работает до остановки вручную.