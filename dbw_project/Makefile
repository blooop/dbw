# DBW Development Makefile

.PHONY: help install test lint format type-check clean build docker-test docs

help: ## Show this help message
	@echo "DBW Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	poetry install --with dev

test: ## Run all tests
	poetry run pytest -v

test-unit: ## Run unit tests only
	poetry run pytest tests/unit -v

test-integration: ## Run integration tests (requires Docker)
	poetry run pytest tests/integration -v

test-cov: ## Run tests with coverage
	poetry run pytest --cov=src/dbw --cov-report=html --cov-report=term

lint: ## Run linter
	poetry run ruff check src/ tests/

lint-fix: ## Fix linting issues automatically
	poetry run ruff check --fix src/ tests/

format: ## Format code
	poetry run black src/ tests/

format-check: ## Check code formatting
	poetry run black --check src/ tests/

type-check: ## Run type checker
	poetry run mypy src/dbw

check: lint format-check type-check ## Run all code quality checks

clean: ## Clean up build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build package
	poetry build

docker-test: ## Test Docker functionality
	./scripts/docker-setup.sh status
	docker buildx build --tag dbw-test:latest --file templates/Dockerfile.base .

docker-ext-test: ## Test extension builds
	cd extensions/fzf && docker buildx build --tag dbw-ext-fzf:test .
	cd extensions/uv && docker buildx build --tag dbw-ext-uv:test .

docs: ## Generate documentation
	@echo "Documentation is in README.md, CONTRIBUTING.md, and docstrings"
	@echo "To view coverage report: make test-cov && open htmlcov/index.html"

release-check: ## Check if ready for release
	@echo "Running release checks..."
	$(MAKE) check
	$(MAKE) test
	@echo "✓ All checks passed! Ready for release."

dev-setup: ## Set up development environment
	@echo "Setting up DBW development environment..."
	poetry install --with dev
	poetry run pre-commit install
	@echo "✓ Development environment ready!"
	@echo ""
	@echo "Quick start:"
	@echo "  make test          # Run tests"
	@echo "  make check         # Run code quality checks"
	@echo "  make docker-test   # Test Docker integration"

# CI targets
ci-test: ## Run tests for CI
	pytest tests/unit -v --cov=src/dbw --cov-report=xml

ci-integration: ## Run integration tests for CI
	pytest tests/integration -v

ci-lint: ## Run linting for CI
	ruff check src/ tests/
	black --check src/ tests/
	mypy src/dbw

# Docker targets
docker-build-base: ## Build base Docker image
	docker buildx build \
		--tag dbw/ubuntu-base:latest \
		--file templates/Dockerfile.base \
		--load \
		.

docker-build-extensions: ## Build all extension images
	@for ext in extensions/*/; do \
		if [ -f "$$ext/Dockerfile" ]; then \
			name=$$(basename $$ext); \
			echo "Building extension: $$name"; \
			docker buildx build \
				--tag "dbw-ext-$$name:latest" \
				--file "$$ext/Dockerfile" \
				--load \
				"$$ext"; \
		fi \
	done

docker-clean: ## Clean up Docker images and containers
	docker system prune -f
	docker images -q "dbw*" | xargs -r docker rmi

# Development helpers
watch-tests: ## Watch files and run tests on changes
	poetry run ptw tests/ src/ --runner "pytest tests/unit -v"

install-hooks: ## Install git hooks
	poetry run pre-commit install

run-hooks: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

# Package management
update-deps: ## Update dependencies
	poetry update

lock-deps: ## Lock dependencies
	poetry lock

# Local development
local-install: ## Install package locally in editable mode
	pip install -e .

local-uninstall: ## Uninstall local package
	pip uninstall dbw -y

# Testing with different Python versions
test-py39: ## Test with Python 3.9
	poetry env use python3.9
	poetry install --with dev
	poetry run pytest

test-py310: ## Test with Python 3.10
	poetry env use python3.10
	poetry install --with dev
	poetry run pytest

test-py311: ## Test with Python 3.11
	poetry env use python3.11
	poetry install --with dev
	poetry run pytest

test-py312: ## Test with Python 3.12
	poetry env use python3.12
	poetry install --with dev
	poetry run pytest