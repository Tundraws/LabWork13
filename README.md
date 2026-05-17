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

После Go-агентов отдельный Python LLM-агент формирует рекомендацию по рискам поставки. Агенты общаются через NATS, сохраняют состояние и счётчики в Redis, а события выполнения можно смотреть через REST API, web-dashboard и Jaeger.

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
- `src/llm-agent` — отдельный Python LLM-агент для генерации риск-рекомендаций. По умолчанию работает в offline-режиме, при `OLLAMA_URL` использует Ollama.
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

Ответ содержит список ставок агентов и выбранного победителя с минимальной стоимостью.

Проверка решения autoscaler для роли forecast:

```bash
curl -X POST http://localhost:8000/api/v1/scaling/forecast
```

Dashboard на `/` содержит форму ручного запуска pipeline и таблицу событий системы.

## LLM-агент

Ollama устанавливать не обязательно. LLM-агент запускается отдельным контейнером и по умолчанию использует детерминированный offline provider, чтобы лабораторная работала без GPU, API-ключей и скачивания модели.

Если нужно подключить локальную Ollama, добавьте переменные окружения для сервиса `llm-agent`:

```yaml
OLLAMA_URL: http://host.docker.internal:11434
OLLAMA_MODEL: llama3.1
```

## Масштабирование агентов

Дополнительные экземпляры агента можно запустить средствами Docker Compose:

```bash
docker compose up --scale forecast-agent=3 --scale ordering-agent=2
```

NATS queue group распределит задачи между экземплярами одного типа.

В оркестраторе также есть autoscaler-service: он периодически анализирует последние dispatch-события, записывает scaling decision в журнал и отдаёт решение через `/api/v1/scaling/{role}`. Для учебной проверки это показывает автоматическое принятие решения о масштабировании без привязки к конкретному Docker Desktop API.

## Выполнение заданий повышенной сложности

1. 4 Go-агента: прогнозирование, заказ, трекинг, риски.
2. Pipeline через NATS: forecast -> ordering -> tracking -> risk -> LLM recommendation.
3. OpenTelemetry/Jaeger подключены к Go-агентам, Python-оркестратору и LLM-агенту.
4. Redis хранит состояние и счётчики обработанных задач агентов.
5. Autoscaler-service автоматически оценивает нагрузку и формирует решение о числе реплик.
6. Auction endpoint собирает bids и выбирает winner по минимальной стоимости.
7. Отдельный Python LLM-агент формирует рекомендацию по управлению рисками.
8. Web-dashboard показывает события и позволяет вручную запустить pipeline.
