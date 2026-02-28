# Rune Arc TUI — Makefile
# Process-per-phase orchestrator for Claude Code

BINARY     := rune-arc
CARGO      := cargo
CRATES_DIR := crates
TARGET     := $(CRATES_DIR)/target/release/$(BINARY)
PLUGIN_DIR := ./plugins/rune

# ─── Build ──────────────────────────────────────

.PHONY: build dev install clean

## Build release binary
build:
	cd $(CRATES_DIR) && $(CARGO) build --release -p rune-arc-cli

## Build debug binary (faster compile, slower runtime)
dev:
	cd $(CRATES_DIR) && $(CARGO) build -p rune-arc-cli

## Install to ~/.cargo/bin/
install: build
	cp $(TARGET) "$${CARGO_HOME:-$$HOME/.cargo}/bin/$(BINARY)"
	@echo "Installed $(BINARY) to $${CARGO_HOME:-$$HOME/.cargo}/bin/"

## Remove build artifacts
clean:
	cd $(CRATES_DIR) && $(CARGO) clean

# ─── Test ───────────────────────────────────────

.PHONY: test test-crate test-verbose

## Run all tests
test:
	cd $(CRATES_DIR) && $(CARGO) test --workspace

## Run tests for a single crate (usage: make test-crate CRATE=rune-arc-engine)
test-crate:
	cd $(CRATES_DIR) && $(CARGO) test -p $(CRATE)

## Run tests with output visible
test-verbose:
	cd $(CRATES_DIR) && $(CARGO) test --workspace -- --nocapture

# ─── Lint ───────────────────────────────────────

.PHONY: check clippy fmt fmt-check

## Type-check without building
check:
	cd $(CRATES_DIR) && $(CARGO) check --workspace

## Run clippy lints
clippy:
	cd $(CRATES_DIR) && $(CARGO) clippy --workspace -- -D warnings

## Format all code
fmt:
	cd $(CRATES_DIR) && $(CARGO) fmt --all

## Check formatting (CI mode)
fmt-check:
	cd $(CRATES_DIR) && $(CARGO) fmt --all -- --check

# ─── Run ────────────────────────────────────────

.PHONY: run run-plain run-fast batch resume status list

## Run arc pipeline with TUI (usage: make run PLAN=plans/my-plan.md)
run: build
	$(TARGET) run $(PLAN) --plugin-dir $(PLUGIN_DIR)

## Run arc pipeline without TUI (plain stdout)
run-plain: build
	$(TARGET) run $(PLAN) --no-tui --plugin-dir $(PLUGIN_DIR)

## Run arc pipeline — skip forge, PR, merge (fast dev loop)
run-fast: build
	$(TARGET) run $(PLAN) --no-tui --no-forge --no-pr --no-merge --plugin-dir $(PLUGIN_DIR)

## Batch mode (usage: make batch GLOB="plans/*.md")
batch: build
	$(TARGET) batch "$(GLOB)" --plugin-dir $(PLUGIN_DIR)

## Resume last interrupted run
resume: build
	$(TARGET) resume

## Show pipeline status
status:
	@$(TARGET) status 2>/dev/null || echo "No active checkpoints"

## List all checkpoints
list:
	@$(TARGET) list 2>/dev/null || echo "No checkpoints found"

# ─── Utilities ──────────────────────────────────

.PHONY: loc deps tree preflight help

## Count lines of Rust code per crate
loc:
	@for crate in rune-arc-proto rune-arc-engine rune-arc-native rune-arc-tui rune-arc-cli; do \
		printf "%-18s" "$$crate:"; \
		find $(CRATES_DIR)/$$crate/src -name '*.rs' | xargs wc -l | tail -1 | awk '{print $$1, "lines"}'; \
	done
	@echo "──────────────────────────"
	@printf "%-18s" "total:"; \
	find $(CRATES_DIR) -path '*/src/*.rs' -not -path '*/target/*' | xargs wc -l | tail -1 | awk '{print $$1, "lines"}'

## Show dependency tree
deps:
	cd $(CRATES_DIR) && $(CARGO) tree --workspace --depth 1

## Show full dependency tree
tree:
	cd $(CRATES_DIR) && $(CARGO) tree --workspace

## Pre-flight check — verify everything needed to run
preflight:
	@echo "Checking prerequisites..."
	@printf "  cargo:      " && cargo --version
	@printf "  rustc:      " && rustc --version
	@printf "  claude:     " && (claude --version 2>/dev/null || echo "NOT FOUND")
	@printf "  gh:         " && (gh --version 2>/dev/null | head -1 || echo "NOT FOUND")
	@printf "  plugin-dir: " && (test -d $(PLUGIN_DIR) && echo "OK" || echo "NOT FOUND")
	@printf "  binary:     " && (test -f $(TARGET) && echo "OK" || echo "not built (run: make build)")
	@echo "Done."

## Show this help
help:
	@echo "Rune Arc TUI — Makefile targets"
	@echo ""
	@echo "Build:"
	@echo "  make build        Build release binary"
	@echo "  make dev          Build debug binary (fast compile)"
	@echo "  make install      Install to ~/.cargo/bin/"
	@echo "  make clean        Remove build artifacts"
	@echo ""
	@echo "Test:"
	@echo "  make test         Run all tests"
	@echo "  make test-crate CRATE=rune-arc-engine   Run one crate"
	@echo "  make clippy       Run lints"
	@echo "  make fmt          Format code"
	@echo ""
	@echo "Run:"
	@echo "  make run PLAN=plans/x.md          Run with TUI"
	@echo "  make run-plain PLAN=plans/x.md    Run without TUI"
	@echo "  make run-fast PLAN=plans/x.md     Run skip forge/PR/merge"
	@echo "  make batch GLOB=\"plans/*.md\"       Batch mode"
	@echo "  make resume                       Resume interrupted run"
	@echo "  make status                       Show pipeline status"
	@echo "  make list                         List checkpoints"
	@echo ""
	@echo "Utilities:"
	@echo "  make preflight    Check prerequisites"
	@echo "  make loc          Lines of code per crate"
	@echo "  make deps         Dependency tree"
	@echo "  make help         This message"

.DEFAULT_GOAL := help
