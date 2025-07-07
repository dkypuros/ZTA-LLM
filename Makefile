# ZTA-LLM Development Makefile

.PHONY: help build start stop test security-test benchmark clean setup-dev lint

# Default target
help:
	@echo "Available targets:"
	@echo "  setup-dev      - Set up development environment"
	@echo "  build          - Build all Docker containers"
	@echo "  start          - Start the development stack"
	@echo "  stop           - Stop all services"
	@echo "  test           - Run unit and integration tests"
	@echo "  security-test  - Run red team security tests"
	@echo "  benchmark      - Run performance benchmarks"
	@echo "  lint           - Run code linting and formatting"
	@echo "  clean          - Clean up containers and volumes"
	@echo "  generate-data  - Generate synthetic test data"

# Development setup
setup-dev:
	@echo "Setting up ZTA-LLM development environment..."
	mkdir -p src/{wrapper,agent_client,mcp_server,security,monitoring}
	mkdir -p deploy/{docker,k8s,opa,envoy,monitoring}
	mkdir -p test/{unit,integration,security,performance}
	mkdir -p data/{synthetic_pii,fake_api_keys,file_structures}
	mkdir -p docs ci
	@echo "Creating Python virtual environment..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "Development environment ready!"

# Docker operations
build:
	@echo "Building ZTA-LLM containers..."
	docker-compose build

start:
	@echo "Starting ZTA-LLM development stack..."
	docker-compose up -d
	@echo "Stack started. Access points:"
	@echo "  Security Wrapper: http://localhost:8080"
	@echo "  MCP Server: http://localhost:8081"
	@echo "  vLLM Server: http://localhost:8000"
	@echo "  OPA Server: http://localhost:8181"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"

stop:
	@echo "Stopping ZTA-LLM stack..."
	docker-compose down

# Testing
test:
	@echo "Running unit and integration tests..."
	docker-compose exec security-wrapper python -m pytest /app/test/unit /app/test/integration -v

security-test:
	@echo "Running security validation tests..."
	docker-compose --profile testing up red-team-tester
	docker-compose logs red-team-tester

benchmark:
	@echo "Running performance benchmarks..."
	docker-compose exec security-wrapper python /app/test/performance/benchmark_suite.py

# Code quality
lint:
	@echo "Running code linting..."
	./venv/bin/black src/ test/
	./venv/bin/flake8 src/ test/
	./venv/bin/mypy src/

# Data generation
generate-data:
	@echo "Generating synthetic test data..."
	docker-compose --profile tools up data-generator
	@echo "Test data generated in ./data/"

# Cleanup
clean:
	@echo "Cleaning up ZTA-LLM environment..."
	docker-compose down -v
	docker system prune -f
	@echo "Cleanup complete!"

# Development helpers
logs:
	docker-compose logs -f

shell-wrapper:
	docker-compose exec security-wrapper /bin/bash

shell-mcp:
	docker-compose exec mcp-server /bin/bash

# Security validation shortcuts
test-secret-injection:
	@echo "Testing secret injection resistance..."
	docker-compose exec red-team-tester python /app/tests/test_secret_injection.py

test-context-accumulation:
	@echo "Testing context accumulation protection..."
	docker-compose exec red-team-tester python /app/tests/test_context_accumulation.py

test-tool-reflection:
	@echo "Testing tool output reflection prevention..."
	docker-compose exec red-team-tester python /app/tests/test_tool_reflection.py

# Performance validation
measure-latency:
	@echo "Measuring security layer latency..."
	docker-compose exec security-wrapper python /app/test/performance/measure_latency.py

# Documentation
docs:
	@echo "Generating documentation..."
	./venv/bin/sphinx-build -b html docs/ docs/_build/

# Install requirements
requirements:
	./venv/bin/pip install -r requirements.txt

# Git hooks setup
hooks:
	cp ci/hooks/pre-commit .git/hooks/
	chmod +x .git/hooks/pre-commit