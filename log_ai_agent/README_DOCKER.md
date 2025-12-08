# Docker Configuration для AI CyberLog Agent

## Структура сервисов

Проект включает 3 сервиса, запускаемых через Docker Compose:

1. **Frontend** - Vue.js веб-интерфейс (порт 3000)
2. **Backend** - Python FastAPI приложение (порт 8000)
3. **Database** - PostgreSQL 16 (порт 5432)

## Быстрый старт

### Запуск всех сервисов

```bash
# Перейти в директорию с docker-compose.yml
cd log_ai_agent

# Запустить все сервисы
docker-compose up -d

# Посмотреть логи
docker-compose logs -f

# Остановить все сервисы
docker-compose down

# Остановить с удалением volumes (очистка БД)
docker-compose down -v
```

### Доступ к сервисам

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### Пересборка образов

```bash
# Пересобрать все образы
docker-compose build

# Пересобрать и запустить
docker-compose up --build -d

# Пересобрать только backend
docker-compose build backend
```

## Управление отдельными сервисами

```bash
# Запустить только базу данных
docker-compose up -d db

# Запустить backend
docker-compose up -d backend

# Запустить frontend
docker-compose up -d frontend

# Остановить конкретный сервис
docker-compose stop backend

# Перезапустить сервис
docker-compose restart backend
```

## Работа с базой данных

### Подключение к PostgreSQL

```bash
# Войти в контейнер с БД
docker-compose exec db psql -U cyberlog_user -d cyberlog_db

# Или через psql на хосте
psql -h localhost -p 5432 -U cyberlog_user -d cyberlog_db
```

Пароль: `cyberlog_password`

### Backup и restore

```bash
# Создать backup
docker-compose exec db pg_dump -U cyberlog_user cyberlog_db > backup.sql

# Восстановить из backup
docker-compose exec -T db psql -U cyberlog_user -d cyberlog_db < backup.sql
```

## Разработка

### Горячая перезагрузка

Backend настроен с `reload=True`, изменения в коде автоматически перезагружают сервер.

Frontend в production режиме (собранный), для разработки лучше запускать локально:

```bash
cd site
npm install
npm run dev
```

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db

# Последние 100 строк
docker-compose logs --tail=100 backend
```

### Проверка состояния

```bash
# Список запущенных контейнеров
docker-compose ps

# Использование ресурсов
docker stats cyberlog-backend cyberlog-frontend cyberlog-db
```

## Переменные окружения

Скопировать `.env.example` в `.env` и настроить при необходимости:

```bash
cp .env.example .env
```

## Volumes

- `postgres_data` - данные PostgreSQL (персистентные)
- `app_logs` - логи приложения

Для очистки volumes:

```bash
docker-compose down -v
```

## Troubleshooting

### Backend не может подключиться к БД

Проверьте, что БД готова:
```bash
docker-compose logs db
```

Проверьте health check:
```bash
docker-compose ps
```

### Порты заняты

Измените порты в `docker-compose.yml`:
```yaml
ports:
  - "3001:80"  # frontend на порту 3001 вместо 3000
  - "8001:8000"  # backend на порту 8001 вместо 8000
```

### Пересоздать все с нуля

```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Production

Для production рекомендуется:

1. Изменить пароли в `.env`
2. Настроить CORS с конкретными доменами
3. Использовать SSL/TLS
4. Настроить мониторинг и логирование
5. Использовать внешний PostgreSQL или managed DB
6. Добавить rate limiting и аутентификацию

## Полезные команды

```bash
# Войти в контейнер backend
docker-compose exec backend bash

# Войти в контейнер frontend
docker-compose exec frontend sh

# Выполнить Python команду в backend
docker-compose exec backend python -c "print('Hello from container')"

# Посмотреть переменные окружения
docker-compose exec backend env
```
