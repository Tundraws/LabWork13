# Лабораторная работа №13

**Студент:** Гуляев Евгений Александрович  
**Группа:** 221331  
**Вариант:** 25  
**Тип варианта:** повышенная сложность  
**Тема:** Мультиагентные системы: разработка распределённых интеллектуальных агентов  
**Предметная область:** управление цепочками поставок

## Описание программы

Проект реализует распределённую мультиагентную систему для управления цепочками поставок. Оркестратор принимает запрос на планирование поставки товара и последовательно запускает pipeline:

1. агент прогнозирования спроса;
2. агент заказа у поставщиков;
3. агент отслеживания поставок;
4. агент управления рисками.

Агенты общаются через NATS, сохраняют состояние и счётчики в Redis, а события выполнения можно смотреть через REST API, web-dashboard и Jaeger.

## Технологии

- Go 1.22: микросервисы агентов, NATS client, Redis client, OpenTelemetry.
- Python 3.12: FastAPI, asyncio, nats-py, Pydantic, pytest.
- NATS: брокер сообщений.
- Redis: хранение состояния агентов.
- Jaeger/OpenTelemetry: распределённая трассировка.
- Docker Compose: локальный запуск инфраструктуры.

## Архитектура

Исходный код расположен в `src/`, тесты — в `tests/`.

- `src/agents` — универсальный Go-агент, специализация задаётся YAML-файлами из `configs/agents`.
- `src/orchestrator` — Python API, оркестратор pipeline, dashboard и LLM-ready risk advisor.
- `tests/python` — unit-тесты оркестратора и схем.
- `src/agents/internal/domain/processor_test.go` — unit-тесты бизнес-логики Go-агентов.

Диаграмма взаимодействия находится в `docs/architecture.md`.

## Сборка

```bash
cp .env.example .env
docker compose build
```

Для локального запуска тестов без Docker:

```bash
python -m pip install -r requirements.txt
cd src/agents && go mod download && go test ./...
cd ../.. && python -m pytest tests/python
```

## Запуск

```bash
docker compose up --build
```

После запуска доступны:

- API и dashboard: http://localhost:8000
- Swagger/OpenAPI: http://localhost:8000/docs
- Jaeger UI: http://localhost:16686
- NATS monitoring: http://localhost:8222

## Примеры запросов

Запуск полного pipeline:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "SKU-25",
    "avg_daily_sales": 18,
    "seasonality_index": 1.3,
    "planning_days": 14,
    "current_stock": 120,
    "unit_price": 9.9
  }'
```

Просмотр событий системы:

```bash
curl http://localhost:8000/api/v1/events
```

Запрос аукционного распределения для роли прогнозирования:

```bash
curl -X POST http://localhost:8000/api/v1/auction/forecast \
  -H "Content-Type: application/json" \
  -d '{"sku":"SKU-25","avg_daily_sales":18,"seasonality_index":1.3,"planning_days":14,"current_stock":120}'
```

## Масштабирование агентов

Дополнительные экземпляры агента можно запустить средствами Docker Compose:

```bash
docker compose up --scale forecast-agent=3 --scale ordering-agent=2
```

NATS queue group распределит задачи между экземплярами одного типа.
