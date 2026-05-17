.PHONY: test test-go test-python compose-up compose-down

test: test-go test-python

test-go:
	cd src/agents && go test ./...

test-python:
	python -m pytest tests/python

compose-up:
	docker compose up --build

compose-down:
	docker compose down --remove-orphans
