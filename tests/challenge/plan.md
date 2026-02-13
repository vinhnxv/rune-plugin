---
title: "feat: dataweaver — multi-format data pipeline CLI"
type: feat
date: 2026-02-13
---

# dataweaver — Multi-Format Data Pipeline CLI

## Overview

Build a Python CLI tool called `dataweaver` that reads data from CSV/JSON/YAML files, applies a chain of transformations (filter, map, aggregate, join), and outputs results to various formats. The tool uses pipeline definitions in YAML to describe data flows.

## Problem Statement

Data engineers frequently need to transform data between formats and apply common operations (filtering, aggregation, joining). Current solutions either require full programming (pandas scripts) or are limited to single operations (csvkit). `dataweaver` provides a declarative YAML-based pipeline that chains multiple transforms.

## Proposed Solution

A Python CLI using `argparse` with four commands: `run`, `validate`, `inspect`, and `convert`. Pipelines are defined in YAML files with source, transforms, and sink sections.

## Technical Approach

### Project Structure

**Inputs**: CLI arguments and YAML pipeline files
**Outputs**: Transformed data in CSV/JSON/YAML format
**Preconditions**: Python 3.11+, PyYAML installed
**Error handling**: Invalid YAML → clear error with line number. Missing source file → FileNotFoundError with path. Invalid column reference → ValueError listing available columns.

```
dataweaver/
├── __init__.py
├── __main__.py          # CLI entry point
├── cli.py               # Argument parsing
├── pipeline.py          # Pipeline loading and validation
├── transforms.py        # Transform implementations
├── io_handlers.py       # Read/write for CSV, JSON, YAML
└── errors.py            # Custom exceptions
tests/
├── test_transforms.py   # Unit tests for transforms
├── test_pipeline.py     # Pipeline loading tests
├── test_cli.py          # CLI integration tests
└── fixtures/            # Test data files
    ├── sample.csv
    ├── sample.json
    └── sample_pipeline.yml
```

### Core Data Model

**Inputs**: Raw file data (CSV rows, JSON objects, YAML documents)
**Outputs**: List of dicts (uniform row format)
**Preconditions**: Source file exists and is readable
**Error handling**: Encoding errors → fallback to utf-8 with replacement chars. Empty file → return empty list with warning.

Data flows through the pipeline as `list[dict[str, Any]]`. Each transform receives and returns this format.

### Transform Implementations

**Inputs**: Data rows (list[dict]) + transform config from YAML
**Outputs**: Transformed data rows (list[dict])
**Preconditions**: Referenced columns must exist in data
**Error handling**: Missing column → raise TransformError with column name and available columns. Type mismatch in comparison → attempt coercion, raise on failure.

#### Filter Transform
Supports operators: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `contains`, `regex`.

#### Map Transform
Supports functions: `upper`, `lower`, `strip`, `round`, `abs`.

#### Aggregate Transform
Supports functions: `mean`, `sum`, `count`, `min`, `max`.
Groups by specified columns, applies aggregate functions.

#### Join Transform
Supports join types: `left`, `right`, `inner`, `outer`.
Joins current data with another file on specified column.

### CLI Commands

**Inputs**: Command name + arguments from argparse
**Outputs**: Depends on command (see below)
**Preconditions**: Valid command provided
**Error handling**: Unknown command → argparse error with usage. Missing required arg → argparse error.

- `run <pipeline.yml>` — Execute a full pipeline. Supports `--dry-run` flag.
- `validate <pipeline.yml>` — Check pipeline definition without executing.
- `inspect <file>` — Show file schema (columns, types, row count).
- `convert <input> <output>` — Direct format conversion.

## Acceptance Criteria

- [ ] CLI parses all commands (run, validate, inspect, convert) with correct argument handling
- [ ] Reads CSV, JSON, YAML input formats with automatic format detection from file extension
- [ ] Applies filter transforms with operators: eq, neq, gt, gte, lt, lte, contains, regex
- [ ] Applies map transforms with functions: upper, lower, strip, round, abs
- [ ] Applies aggregate transforms with: mean, sum, count, min, max
- [ ] Applies join transforms with: left, right, inner, outer join types
- [ ] Outputs to CSV, JSON, YAML formats
- [ ] Error handling: malformed input files produce clear error messages
- [ ] Pipeline validation catches missing files and invalid column references
- [ ] Unit tests cover core transform functions
- [ ] CLI --help produces usage information for all commands
- [ ] `--dry-run` flag shows execution plan without writing output

## Dependencies & Risks

- **Dependencies**: Python 3.11+, PyYAML
- **Risk**: Complex aggregate + join chains may have edge cases with empty groups
- **Mitigation**: Comprehensive test fixtures with edge cases

## References

- Python argparse: https://docs.python.org/3/library/argparse.html
- PyYAML: https://pyyaml.org/
