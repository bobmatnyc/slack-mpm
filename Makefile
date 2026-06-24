# ============================================================================
# Slack MPM - MCP Server for Slack
# ============================================================================
# Automates development, testing, and publishing workflows
#
# Quick start:
#   make help          - Show this help
#   make install       - Install package in dev mode
#   make test          - Run pytest
#   make build         - Build wheel and sdist
#   make publish       - Bump patch + build + publish to PyPI + GitHub Release
#
# Version & Release:
#   make version       - Show current version
#   make bump-patch    - Bump patch version (0.1.1 -> 0.1.2)
#   make bump-minor    - Bump minor version (0.1.1 -> 0.2.0)
#   make bump-major    - Bump major version (0.1.1 -> 1.0.0)
#   make publish       - Full patch release: bump + build + PyPI + GitHub
#   make publish-minor - Full minor release
#   make publish-major - Full major release
#   make publish-only  - Publish current version to PyPI (no bump)

# ============================================================================
# PHONY Target Declarations
# ============================================================================
.PHONY: help install install-dev test lint format type-check clean build
.PHONY: publish publish-minor publish-major publish-only pre-publish
.PHONY: version bump-patch bump-minor bump-major sync-versions
.PHONY: tag push push-tags

# ============================================================================
# Shell Configuration (Strict Mode)
# ============================================================================
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ============================================================================
# Configuration Variables
# ============================================================================
BLUE  := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED   := \033[0;31m
NC    := \033[0m

BUILD_DIR := build
DIST_DIR  := dist
PYTHON    := uv run python
PACKAGE   := slack_mpm

all: help

# ============================================================================
# Help System
# ============================================================================

help: ## Show this help message
	@echo "Slack MPM - MCP Server for Slack"
	@echo "================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "$(BLUE)Version Management:$(NC)"
	@echo "  $(GREEN)make version$(NC)        - Show current version"
	@echo "  $(GREEN)make bump-patch$(NC)     - Bump patch version (x.y.Z+1)"
	@echo "  $(GREEN)make bump-minor$(NC)     - Bump minor version (x.Y+1.0)"
	@echo "  $(GREEN)make bump-major$(NC)     - Bump major version (X+1.0.0)"
	@echo ""
	@echo "$(BLUE)Publishing:$(NC)"
	@echo "  $(GREEN)make publish$(NC)        - Patch bump + build + PyPI + GitHub Release"
	@echo "  $(GREEN)make publish-minor$(NC)  - Minor bump + build + PyPI + GitHub Release"
	@echo "  $(GREEN)make publish-major$(NC)  - Major bump + build + PyPI + GitHub Release"
	@echo "  $(GREEN)make publish-only$(NC)   - Publish current version to PyPI (no bump)"
	@echo ""
	@echo "$(BLUE)Git Operations:$(NC)"
	@echo "  $(GREEN)make tag$(NC)            - Create git tag for current version"
	@echo "  $(GREEN)make push$(NC)           - Push commits to origin"
	@echo "  $(GREEN)make push-tags$(NC)      - Push tags to origin"
	@echo ""
	@echo "$(BLUE)Development:$(NC)"
	@echo "  $(GREEN)make install$(NC)        - Install package in dev mode"
	@echo "  $(GREEN)make test$(NC)           - Run pytest"
	@echo "  $(GREEN)make lint$(NC)           - Run ruff linter"
	@echo "  $(GREEN)make format$(NC)         - Format code with ruff"
	@echo "  $(GREEN)make type-check$(NC)     - Run mypy type checker"
	@echo "  $(GREEN)make build$(NC)          - Build wheel and sdist"
	@echo "  $(GREEN)make clean$(NC)          - Remove build artifacts"
	@echo ""
	@echo "$(BLUE)Version:$(NC) $$(cat VERSION 2>/dev/null || echo 'unknown')"

# ============================================================================
# Installation
# ============================================================================

install: ## Install package in development mode
	@echo "$(YELLOW)Installing slack-mpm in dev mode...$(NC)"
	uv sync
	@echo "$(GREEN)Done. Run 'uv run slack-mpm --help' to verify.$(NC)"

install-dev: ## Install package with dev dependencies
	@echo "$(YELLOW)Installing slack-mpm with dev dependencies...$(NC)"
	uv sync --extra dev
	@echo "$(GREEN)Done.$(NC)"

# ============================================================================
# Testing
# ============================================================================

test: ## Run pytest
	@echo "$(YELLOW)Running tests...$(NC)"
	uv run python -m pytest tests/ -v
	@echo "$(GREEN)Tests completed.$(NC)"

test-cov: ## Run pytest with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	uv run python -m pytest tests/ -v --cov=src/$(PACKAGE) --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# ============================================================================
# Linting & Formatting
# ============================================================================

lint: ## Run ruff linter
	@echo "$(YELLOW)Running ruff linter...$(NC)"
	uv run ruff check src/ tests/ || exit 1
	@echo "$(GREEN)Linting passed.$(NC)"

format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	uv run ruff check src/ tests/ --fix || true
	uv run ruff format src/ tests/
	@echo "$(GREEN)Formatting complete.$(NC)"

type-check: ## Run mypy type checker
	@echo "$(YELLOW)Running type checks...$(NC)"
	uv run mypy src/ --ignore-missing-imports || true
	@echo "$(GREEN)Type check complete.$(NC)"

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info src/*.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete.$(NC)"

# ============================================================================
# Build
# ============================================================================

build: clean ## Build wheel and sdist
	@echo "$(YELLOW)Building package...$(NC)"
	uv build
	@echo "$(GREEN)Build complete.$(NC)"
	@ls -la $(DIST_DIR)/

# ============================================================================
# Version Management
# ============================================================================

version: ## Show current version
	@cat VERSION

sync-versions: ## Sync version from VERSION file into pyproject.toml and __version__.py
	@echo "$(YELLOW)Syncing version files...$(NC)"
	@VERSION=$$(cat VERSION); \
	sed -i '' "s/^version = \"[^\"]*\"/version = \"$$VERSION\"/" pyproject.toml 2>/dev/null || \
	sed -i  "s/^version = \"[^\"]*\"/version = \"$$VERSION\"/" pyproject.toml; \
	sed -i '' "s/^__version__ = \"[^\"]*\"/__version__ = \"$$VERSION\"/" src/slack_mpm/__version__.py 2>/dev/null || \
	sed -i  "s/^__version__ = \"[^\"]*\"/__version__ = \"$$VERSION\"/" src/slack_mpm/__version__.py; \
	echo "$(GREEN)Synced to version $$VERSION$(NC)"

bump-patch: ## Bump patch version (x.y.Z+1)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

bump-minor: ## Bump minor version (x.Y+1.0)
	@echo "$(YELLOW)Bumping minor version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

bump-major: ## Bump major version (X+1.0.0)
	@echo "$(YELLOW)Bumping major version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

# ============================================================================
# Git Operations
# ============================================================================

tag: ## Create git tag for current version
	@VERSION=$$(cat VERSION); \
	echo "$(YELLOW)Creating tag v$$VERSION...$(NC)"; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	echo "$(GREEN)Tag v$$VERSION created$(NC)"

push: ## Push commits to origin
	@echo "$(YELLOW)Pushing commits to origin...$(NC)"
	git push origin
	@echo "$(GREEN)Commits pushed$(NC)"

push-tags: ## Push tags to origin
	@echo "$(YELLOW)Pushing tags to origin...$(NC)"
	git push origin --tags
	@echo "$(GREEN)Tags pushed$(NC)"

# ============================================================================
# PyPI Token Resolution
# Looks in (in order):
#   1. .env.local (local project override)
#   2. ../gworkspace-mcp/.env.local (shared creds)
# ============================================================================

_load-pypi-token:
	@if [ -f .env.local ]; then \
		. .env.local; \
	fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then \
		. ../gworkspace-mcp/.env.local; \
	fi; \
	if [ -z "$${PYPI_TOKEN:-}" ]; then \
		echo "$(RED)Error: PYPI_TOKEN not found.$(NC)"; \
		echo "$(YELLOW)Set it in .env.local or ../gworkspace-mcp/.env.local$(NC)"; \
		exit 1; \
	fi

# ============================================================================
# Pre-Publish Quality Gate
# ============================================================================

pre-publish: lint test ## Run quality checks before publishing
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(BLUE)Pre-Publish Quality Gate$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking working directory...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory has uncommitted changes. Commit or stash all changes before publishing.$(NC)"; \
		echo "$(YELLOW)Dirty files:$(NC)"; \
		git status --porcelain 2>/dev/null; \
		exit 1; \
	else \
		echo "$(GREEN)Working directory is clean.$(NC)"; \
	fi
	@echo ""
	@echo "$(YELLOW)Checking PyPI token...$(NC)"
	@PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ]; then \
		echo "$(RED)Error: PYPI_TOKEN not found in .env.local or ../gworkspace-mcp/.env.local$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)PYPI_TOKEN found.$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)============================================$(NC)"
	@echo "$(GREEN)Pre-publish checks PASSED!$(NC)"
	@echo "$(GREEN)============================================$(NC)"

# ============================================================================
# Publish Targets
# ============================================================================

define _do_publish
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_VERSION=$(1); \
	echo "$(YELLOW)Version: $$CURRENT -> $$NEW_VERSION$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	echo "$(GREEN)Version bumped$(NC)"; \
	git add VERSION pyproject.toml; \
	git commit -m "chore: bump version to $$NEW_VERSION"; \
	echo "$(GREEN)Committed$(NC)"; \
	git tag "v$$NEW_VERSION"; \
	echo "$(GREEN)Tagged v$$NEW_VERSION$(NC)"; \
	git push && git push --tags; \
	echo "$(GREEN)Pushed to origin$(NC)"; \
	$(MAKE) build; \
	PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	UV_PUBLISH_TOKEN="$$PYPI_TOKEN" uv publish && \
	echo "$(GREEN)Published to PyPI$(NC)"; \
	if command -v gh >/dev/null 2>&1; then \
		gh release create "v$$NEW_VERSION" \
			--title "v$$NEW_VERSION" \
			--generate-notes \
			dist/* && echo "$(GREEN)GitHub Release created$(NC)" || echo "$(YELLOW)GitHub Release skipped$(NC)"; \
	else \
		echo "$(YELLOW)gh CLI not found - skipping GitHub Release$(NC)"; \
	fi
endef

publish: ## Bump patch + build + publish to PyPI + GitHub Release
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Patch Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$(YELLOW)Version: $$CURRENT -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Idempotency check: verifying v$$NEW_VERSION is not already released...$(NC)"; \
	if git tag | grep -q "^v$$NEW_VERSION$$"; then \
		echo "$(RED)Error: local git tag v$$NEW_VERSION already exists. The version has already been released or bumped.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	if git ls-remote --tags origin "refs/tags/v$$NEW_VERSION" 2>/dev/null | grep -q "refs/tags/v$$NEW_VERSION"; then \
		echo "$(RED)Error: remote git tag v$$NEW_VERSION already exists. The version has already been released.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	# Note: the PyPI pre-check below is best-effort — a concurrent publish from another \
	# machine could race past it. uv publish --check-url is the upload-time backstop. \
	HTTP_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/slack-mpm/$$NEW_VERSION/json"); \
	if [ "$$HTTP_STATUS" = "200" ]; then \
		echo "$(RED)Error: v$$NEW_VERSION already exists on PyPI. The version has already been published.$(NC)"; \
		echo "$(YELLOW)Bump the version manually or increment to a fresh version number.$(NC)"; \
		exit 1; \
	elif [ "$$HTTP_STATUS" != "404" ]; then \
		echo "$(RED)Error: Could not verify PyPI state (HTTP $$HTTP_STATUS) — aborting before any changes.$(NC)"; \
		echo "$(YELLOW)It is safe to re-run make publish once connectivity is restored.$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Idempotency check passed: v$$NEW_VERSION is a fresh release.$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	$(MAKE) build; \
	PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	# uv publish uses --check-url (not --skip-existing) to skip duplicate uploads at upload time. \
	# Requires uv >= 0.4.x (installed: uv 0.11.16). \
	if UV_PUBLISH_TOKEN="$$PYPI_TOKEN" uv publish --check-url https://pypi.org/simple/; then \
		echo "$(GREEN)Published to PyPI$(NC)"; \
		# Commit+tag LOCALLY first, then push. \
		# If git push fails: repo has a clean local commit+tag; recovery = git push && git push --tags. \
		# Do NOT re-run make publish — the PyPI 200 guard will correctly block it. \
		if git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock && \
		   git commit -m "chore: bump version to $$NEW_VERSION" && \
		   git tag "v$$NEW_VERSION" && \
		   git push && git push --tags; then \
			echo "$(GREEN)Committed, tagged, pushed$(NC)"; \
			if command -v gh >/dev/null 2>&1; then \
				gh release create "v$$NEW_VERSION" --title "v$$NEW_VERSION" --generate-notes dist/* \
					&& echo "$(GREEN)GitHub Release created$(NC)" \
					|| echo "$(YELLOW)GitHub Release skipped$(NC)"; \
			else \
				echo "$(YELLOW)gh CLI not found - skipping GitHub Release$(NC)"; \
			fi; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
			echo "$(GREEN)  Published slack-mpm $$NEW_VERSION$(NC)"; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
		else \
			echo "$(RED)PyPI publish SUCCEEDED but git commit/tag/push FAILED.$(NC)"; \
			echo "$(RED)The package v$$NEW_VERSION is live on PyPI.$(NC)"; \
			echo "$(YELLOW)Do NOT re-run make publish — the idempotency guard will block it (version already on PyPI).$(NC)"; \
			echo "$(YELLOW)Recover manually:$(NC)"; \
			echo "$(YELLOW)  git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock$(NC)"; \
			echo "$(YELLOW)  git commit -m 'chore: bump version to $$NEW_VERSION'$(NC)"; \
			echo "$(YELLOW)  git tag v$$NEW_VERSION$(NC)"; \
			echo "$(YELLOW)  git push && git push --tags$(NC)"; \
			echo "$(YELLOW)  gh release create v$$NEW_VERSION --title v$$NEW_VERSION --generate-notes dist/*$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)PyPI publish FAILED. Reverting version files to restore clean tree...$(NC)"; \
		git checkout -- VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock; \
		echo "$(YELLOW)Version files reverted. Tree is clean. Fix the publish error and re-run make publish.$(NC)"; \
		exit 1; \
	fi

publish-minor: ## Bump minor + build + publish to PyPI + GitHub Release
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Minor Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$(YELLOW)Version: $$CURRENT -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Idempotency check: verifying v$$NEW_VERSION is not already released...$(NC)"; \
	if git tag | grep -q "^v$$NEW_VERSION$$"; then \
		echo "$(RED)Error: local git tag v$$NEW_VERSION already exists. The version has already been released or bumped.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	if git ls-remote --tags origin "refs/tags/v$$NEW_VERSION" 2>/dev/null | grep -q "refs/tags/v$$NEW_VERSION"; then \
		echo "$(RED)Error: remote git tag v$$NEW_VERSION already exists. The version has already been released.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	# Note: the PyPI pre-check below is best-effort — a concurrent publish from another \
	# machine could race past it. uv publish --check-url is the upload-time backstop. \
	HTTP_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/slack-mpm/$$NEW_VERSION/json"); \
	if [ "$$HTTP_STATUS" = "200" ]; then \
		echo "$(RED)Error: v$$NEW_VERSION already exists on PyPI. The version has already been published.$(NC)"; \
		echo "$(YELLOW)Bump the version manually or increment to a fresh version number.$(NC)"; \
		exit 1; \
	elif [ "$$HTTP_STATUS" != "404" ]; then \
		echo "$(RED)Error: Could not verify PyPI state (HTTP $$HTTP_STATUS) — aborting before any changes.$(NC)"; \
		echo "$(YELLOW)It is safe to re-run make publish once connectivity is restored.$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Idempotency check passed: v$$NEW_VERSION is a fresh release.$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	$(MAKE) build; \
	PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	# uv publish uses --check-url (not --skip-existing) to skip duplicate uploads at upload time. \
	# Requires uv >= 0.4.x (installed: uv 0.11.16). \
	if UV_PUBLISH_TOKEN="$$PYPI_TOKEN" uv publish --check-url https://pypi.org/simple/; then \
		echo "$(GREEN)Published to PyPI$(NC)"; \
		# Commit+tag LOCALLY first, then push. \
		# If git push fails: repo has a clean local commit+tag; recovery = git push && git push --tags. \
		# Do NOT re-run make publish — the PyPI 200 guard will correctly block it. \
		if git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock && \
		   git commit -m "chore: bump version to $$NEW_VERSION" && \
		   git tag "v$$NEW_VERSION" && \
		   git push && git push --tags; then \
			echo "$(GREEN)Committed, tagged, pushed$(NC)"; \
			if command -v gh >/dev/null 2>&1; then \
				gh release create "v$$NEW_VERSION" --title "v$$NEW_VERSION" --generate-notes dist/* \
					&& echo "$(GREEN)GitHub Release created$(NC)" \
					|| echo "$(YELLOW)GitHub Release skipped$(NC)"; \
			else \
				echo "$(YELLOW)gh CLI not found - skipping GitHub Release$(NC)"; \
			fi; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
			echo "$(GREEN)  Published slack-mpm $$NEW_VERSION$(NC)"; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
		else \
			echo "$(RED)PyPI publish SUCCEEDED but git commit/tag/push FAILED.$(NC)"; \
			echo "$(RED)The package v$$NEW_VERSION is live on PyPI.$(NC)"; \
			echo "$(YELLOW)Do NOT re-run make publish — the idempotency guard will block it (version already on PyPI).$(NC)"; \
			echo "$(YELLOW)Recover manually:$(NC)"; \
			echo "$(YELLOW)  git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock$(NC)"; \
			echo "$(YELLOW)  git commit -m 'chore: bump version to $$NEW_VERSION'$(NC)"; \
			echo "$(YELLOW)  git tag v$$NEW_VERSION$(NC)"; \
			echo "$(YELLOW)  git push && git push --tags$(NC)"; \
			echo "$(YELLOW)  gh release create v$$NEW_VERSION --title v$$NEW_VERSION --generate-notes dist/*$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)PyPI publish FAILED. Reverting version files to restore clean tree...$(NC)"; \
		git checkout -- VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock; \
		echo "$(YELLOW)Version files reverted. Tree is clean. Fix the publish error and re-run make publish.$(NC)"; \
		exit 1; \
	fi

publish-major: ## Bump major + build + publish to PyPI + GitHub Release
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Major Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$(YELLOW)Version: $$CURRENT -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Idempotency check: verifying v$$NEW_VERSION is not already released...$(NC)"; \
	if git tag | grep -q "^v$$NEW_VERSION$$"; then \
		echo "$(RED)Error: local git tag v$$NEW_VERSION already exists. The version has already been released or bumped.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	if git ls-remote --tags origin "refs/tags/v$$NEW_VERSION" 2>/dev/null | grep -q "refs/tags/v$$NEW_VERSION"; then \
		echo "$(RED)Error: remote git tag v$$NEW_VERSION already exists. The version has already been released.$(NC)"; \
		echo "$(YELLOW)If the publish failed mid-flight, use 'make publish-only' to retry publishing the current version.$(NC)"; \
		exit 1; \
	fi; \
	# Note: the PyPI pre-check below is best-effort — a concurrent publish from another \
	# machine could race past it. uv publish --check-url is the upload-time backstop. \
	HTTP_STATUS=$$(curl -s -o /dev/null -w "%{http_code}" "https://pypi.org/pypi/slack-mpm/$$NEW_VERSION/json"); \
	if [ "$$HTTP_STATUS" = "200" ]; then \
		echo "$(RED)Error: v$$NEW_VERSION already exists on PyPI. The version has already been published.$(NC)"; \
		echo "$(YELLOW)Bump the version manually or increment to a fresh version number.$(NC)"; \
		exit 1; \
	elif [ "$$HTTP_STATUS" != "404" ]; then \
		echo "$(RED)Error: Could not verify PyPI state (HTTP $$HTTP_STATUS) — aborting before any changes.$(NC)"; \
		echo "$(YELLOW)It is safe to re-run make publish once connectivity is restored.$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Idempotency check passed: v$$NEW_VERSION is a fresh release.$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	$(MAKE) build; \
	PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	# uv publish uses --check-url (not --skip-existing) to skip duplicate uploads at upload time. \
	# Requires uv >= 0.4.x (installed: uv 0.11.16). \
	if UV_PUBLISH_TOKEN="$$PYPI_TOKEN" uv publish --check-url https://pypi.org/simple/; then \
		echo "$(GREEN)Published to PyPI$(NC)"; \
		# Commit+tag LOCALLY first, then push. \
		# If git push fails: repo has a clean local commit+tag; recovery = git push && git push --tags. \
		# Do NOT re-run make publish — the PyPI 200 guard will correctly block it. \
		if git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock && \
		   git commit -m "chore: bump version to $$NEW_VERSION" && \
		   git tag "v$$NEW_VERSION" && \
		   git push && git push --tags; then \
			echo "$(GREEN)Committed, tagged, pushed$(NC)"; \
			if command -v gh >/dev/null 2>&1; then \
				gh release create "v$$NEW_VERSION" --title "v$$NEW_VERSION" --generate-notes dist/* \
					&& echo "$(GREEN)GitHub Release created$(NC)" \
					|| echo "$(YELLOW)GitHub Release skipped$(NC)"; \
			else \
				echo "$(YELLOW)gh CLI not found - skipping GitHub Release$(NC)"; \
			fi; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
			echo "$(GREEN)  Published slack-mpm $$NEW_VERSION$(NC)"; \
			echo "$(GREEN)═══════════════════════════════════════════$(NC)"; \
		else \
			echo "$(RED)PyPI publish SUCCEEDED but git commit/tag/push FAILED.$(NC)"; \
			echo "$(RED)The package v$$NEW_VERSION is live on PyPI.$(NC)"; \
			echo "$(YELLOW)Do NOT re-run make publish — the idempotency guard will block it (version already on PyPI).$(NC)"; \
			echo "$(YELLOW)Recover manually:$(NC)"; \
			echo "$(YELLOW)  git add VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock$(NC)"; \
			echo "$(YELLOW)  git commit -m 'chore: bump version to $$NEW_VERSION'$(NC)"; \
			echo "$(YELLOW)  git tag v$$NEW_VERSION$(NC)"; \
			echo "$(YELLOW)  git push && git push --tags$(NC)"; \
			echo "$(YELLOW)  gh release create v$$NEW_VERSION --title v$$NEW_VERSION --generate-notes dist/*$(NC)"; \
			exit 1; \
		fi; \
	else \
		echo "$(RED)PyPI publish FAILED. Reverting version files to restore clean tree...$(NC)"; \
		git checkout -- VERSION pyproject.toml src/slack_mpm/__version__.py uv.lock; \
		echo "$(YELLOW)Version files reverted. Tree is clean. Fix the publish error and re-run make publish.$(NC)"; \
		exit 1; \
	fi

publish-only: ## Publish current version to PyPI (no version bump, safe to retry)
	@echo "$(BLUE)Publishing current version to PyPI...$(NC)"
	@$(MAKE) build
	@PYPI_TOKEN=""; \
	if [ -f .env.local ]; then . .env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ] && [ -f ../gworkspace-mcp/.env.local ]; then . ../gworkspace-mcp/.env.local; fi; \
	if [ -z "$${PYPI_TOKEN:-}" ]; then \
		echo "$(RED)Error: PYPI_TOKEN not found$(NC)"; \
		exit 1; \
	fi; \
	UV_PUBLISH_TOKEN="$$PYPI_TOKEN" uv publish --check-url https://pypi.org/simple/ && \
	echo "$(GREEN)Published to PyPI$(NC)"
