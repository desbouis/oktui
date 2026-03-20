# Common variables
PROJECT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
GIT_CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
PREK_ARGS ?= --from-ref=main --to-ref=$(GIT_CURRENT_BRANCH)

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
	prek clean
	prek install --overwrite --hook-type pre-commit --hook-type commit-msg --hook-type pre-push

pre-commit-run: ## Run pre-commit
	prek run ${PREK_ARGS}

test: pre-commit-run ## Run tests
