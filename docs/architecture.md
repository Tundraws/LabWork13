# Архитектура

```mermaid
flowchart LR
    API[FastAPI API и Dashboard] --> ORCH[Python Orchestrator]
    ORCH -->|NATS: supply.tasks.forecast| F[Go Forecast Agent]
    F -->|NATS: supply.results| ORCH
    ORCH -->|NATS: supply.tasks.ordering| O[Go Ordering Agent]
    O -->|NATS: supply.results| ORCH
    ORCH -->|NATS: supply.tasks.tracking| T[Go Tracking Agent]
    T -->|NATS: supply.results| ORCH
    ORCH -->|NATS: supply.tasks.risk| R[Go Risk Agent]
    R -->|NATS: supply.results| ORCH
    F --> Redis[(Redis state)]
    O --> Redis
    T --> Redis
    R --> Redis
    ORCH -->|NATS: supply.tasks.llm| LLM[Python LLM Agent]
    LLM -->|NATS: supply.llm.results| ORCH
    ORCH --> AS[Autoscaler Service]
    ORCH --> Jaeger[Jaeger traces]
    LLM --> Jaeger
```

Pipeline: прогнозирование спроса -> заказ у поставщика -> отслеживание поставки -> оценка рисков -> LLM-рекомендация.
Агенты реализованы одним универсальным Go-сервисом, специализация задаётся YAML-конфигурацией.
События pipeline доступны в REST API и на dashboard.
