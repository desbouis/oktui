# Common variables
PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

help: ## Display help
	@grep -E '^[a-zA-Z1-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN { FS = ":.*?## " }; { printf "\033[36m%-30s\033[0m %s\n", $$1, $$2 }'

clean: ## Clean before build
	@echo "> Clean well executed!"

build: clean ## Build the app
	@echo "> Build well executed!"

install: ## Install tools
	uv venv --clear
	uv pip install -r $(PROJECT_DIR)/requirements.txt

test: pre-commit-run ## Run tests
	@echo "> Tests well executed!"
