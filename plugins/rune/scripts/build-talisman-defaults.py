#!/usr/bin/env python3
"""
Build talisman-defaults.json from talisman.example.yml.

This is a build-time script — run it manually when the talisman schema changes.
Output is committed to the repo so the runtime resolver never needs PyYAML.

Usage:
    python3 plugins/rune/scripts/build-talisman-defaults.py

Requires: PyYAML (pip install pyyaml)
"""

import json
import os
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
EXAMPLE_FILE = os.path.join(PLUGIN_ROOT, "talisman.example.yml")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "talisman-defaults.json")


def build_defaults():
    """Parse talisman.example.yml and extract all active (uncommented) defaults."""
    if not os.path.isfile(EXAMPLE_FILE):
        print(f"ERROR: {EXAMPLE_FILE} not found", file=sys.stderr)
        sys.exit(1)

    with open(EXAMPLE_FILE, encoding="utf-8-sig") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        print("ERROR: talisman.example.yml is empty or not a mapping", file=sys.stderr)
        sys.exit(1)

    # Add schema version for shard resolver compatibility
    data["_schema_version"] = 1

    # Inject documented defaults for commented-out top-level keys.
    # These keys appear only as comments in the example file but have
    # well-documented default values that the resolver needs.
    _inject_commented_defaults(data)

    output = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
        f.write("\n")

    print(f"OK: wrote {OUTPUT_FILE} ({len(output)} bytes, {len(data)} top-level keys)")


def _inject_commented_defaults(data):
    """
    Inject defaults for keys that are commented out in the example YAML.

    The example file documents these as comments with default values.
    We add them here so the shard resolver has a complete defaults registry.
    """
    # cost_tier (commented out, default: "balanced")
    if "cost_tier" not in data:
        data["cost_tier"] = "balanced"

    # goldmask (commented out entirely)
    if "goldmask" not in data:
        data["goldmask"] = {
            "enabled": True,
            "layers": {
                "impact": {
                    "enabled": True,
                    "tracer_model": "haiku",
                    "max_tracers": 5,
                    "tracer_timeout": 120000,
                },
                "wisdom": {
                    "enabled": True,
                    "model": "sonnet",
                    "max_blame_files": 50,
                    "max_findings_to_investigate": 20,
                    "intent_classification": True,
                    "caution_threshold": 0.7,
                },
                "lore": {
                    "enabled": True,
                    "model": "haiku",
                    "lookback_days": 180,
                    "churn_threshold": 10,
                    "co_change_min_support": 3,
                    "ownership_concentration_warn": 0.8,
                },
                "cdd": {
                    "enabled": True,
                    "noisy_or_threshold": 0.6,
                    "swarm_detection": True,
                    "swarm_lookback_commits": 50,
                },
            },
            "coordinator_model": "sonnet",
            "double_check_top_n": 5,
            "priority_weights": {
                "impact": 0.4,
                "wisdom": 0.35,
                "lore": 0.25,
            },
            "modes": {
                "quick": False,
                "deep": False,
            },
            "forge": {"enabled": True},
            "mend": {
                "enabled": True,
                "inject_context": True,
                "quick_check": True,
            },
            "devise": {
                "enabled": True,
                "depth": "basic",
            },
            "inspect": {
                "enabled": True,
                "wisdom_passthrough": True,
            },
        }

    # plan (commented out entirely)
    if "plan" not in data:
        data["plan"] = {
            "freshness": {
                "enabled": True,
                "warn_threshold": 0.7,
                "block_threshold": 0.4,
                "max_commit_distance": 100,
            },
            "verification_patterns": [],
        }

    # debug (commented out entirely)
    if "debug" not in data:
        data["debug"] = {
            "max_investigators": 4,
            "timeout_ms": 420000,
            "model": "sonnet",
            "re_triage_rounds": 1,
            "echo_on_verdict": True,
        }

    # stack_awareness (commented out entirely)
    if "stack_awareness" not in data:
        data["stack_awareness"] = {
            "enabled": True,
            "confidence_threshold": 0.6,
            "max_stack_ashes": 3,
            "override": None,
            "custom_rules": [],
        }

    # design_sync (commented out entirely)
    if "design_sync" not in data:
        data["design_sync"] = {
            "enabled": False,
            "max_extraction_workers": 2,
            "max_implementation_workers": 3,
            "max_iteration_workers": 2,
            "max_iterations": 5,
            "iterate_enabled": False,
            "fidelity_threshold": 80,
            "token_snap_distance": 20,
            "figma_cache_ttl": 1800,
        }

    # deployment_verification (commented out entirely)
    if "deployment_verification" not in data:
        data["deployment_verification"] = {
            "enabled": False,
            "auto_run_on_migrations": False,
            "output_dir": "tmp/deploy/",
            "monitoring_stack": None,
        }

    # schema_drift (commented out entirely)
    if "schema_drift" not in data:
        data["schema_drift"] = {
            "enabled": True,
            "frameworks": [],
            "strict_mode": False,
            "ignore_paths": [],
        }

    # inner_flame (commented out entirely)
    if "inner_flame" not in data:
        data["inner_flame"] = {
            "enabled": True,
            "block_on_fail": False,
            "confidence_floor": 60,
            "completeness_scoring": {
                "enabled": True,
                "threshold": 0.7,
                "research_threshold": 0.5,
            },
        }

    # question_relay (lives in work section conceptually, but is a top-level key
    # that belongs in misc.json shard per the plan)
    if "question_relay" not in data:
        data["question_relay"] = {
            "max_questions_per_worker": 3,
            "timeout_seconds": 120,
        }

    # arc_hierarchy (commented out — lives under work.hierarchy but also
    # has a standalone arc_hierarchy key for cleanup_child_branches)
    if "arc_hierarchy" not in data:
        data["arc_hierarchy"] = {
            "cleanup_child_branches": True,
        }

    # Ensure review has all commented-out sub-keys with defaults
    review = data.get("review", {})
    if "auto_mend" not in review:
        review["auto_mend"] = False
    if "chunk_threshold" not in review:
        review["chunk_threshold"] = 20
    if "chunk_target_size" not in review:
        review["chunk_target_size"] = 15
    if "max_chunks" not in review:
        review["max_chunks"] = 5
    if "cross_cutting_pass" not in review:
        review["cross_cutting_pass"] = True
    if "diff_scope" not in review:
        review["diff_scope"] = {
            "enabled": True,
            "expansion": 8,
            "tag_pre_existing": True,
            "fix_pre_existing_p1": True,
        }
    if "convergence" not in review:
        review["convergence"] = {
            "smart_scoring": True,
            "convergence_threshold": 0.7,
        }
    if "enforcement_asymmetry" not in review:
        review["enforcement_asymmetry"] = {
            "enabled": True,
            "security_always_strict": True,
            "new_file_threshold": 0.30,
            "high_risk_import_count": 5,
        }
    if "context_intelligence" not in review:
        review["context_intelligence"] = {
            "enabled": True,
            "scope_warning_threshold": 1000,
            "fetch_linked_issues": True,
            "max_pr_body_chars": 3000,
        }
    if "linter_awareness" not in review:
        review["linter_awareness"] = {
            "enabled": True,
            "always_review": [],
        }
    # Arc convergence defaults (under review: namespace per talisman docs)
    if "arc_convergence_tier_override" not in review:
        review["arc_convergence_tier_override"] = None
    if "arc_convergence_max_cycles" not in review:
        review["arc_convergence_max_cycles"] = None
    if "arc_convergence_min_cycles" not in review:
        review["arc_convergence_min_cycles"] = None
    if "arc_convergence_finding_threshold" not in review:
        review["arc_convergence_finding_threshold"] = 0
    if "arc_convergence_p2_threshold" not in review:
        review["arc_convergence_p2_threshold"] = 0
    if "arc_convergence_improvement_ratio" not in review:
        review["arc_convergence_improvement_ratio"] = 0.5
    data["review"] = review

    # Ensure work has all commented-out sub-keys with defaults
    work = data.get("work", {})
    if "worktree" not in work:
        work["worktree"] = {
            "enabled": False,
            "max_workers_per_wave": 3,
            "merge_strategy": "sequential",
            "auto_cleanup": True,
            "conflict_resolution": "escalate",
        }
    if "hierarchy" not in work:
        work["hierarchy"] = {
            "enabled": True,
            "max_children": 12,
            "max_backtracks": 1,
            "missing_prerequisite": "pause",
            "conflict_resolution": "pause",
            "integration_failure": "pause",
            "sync_main_before_pr": True,
            "cleanup_child_branches": True,
            "require_all_children": True,
            "test_timeout_ms": 300000,
            "merge_strategy": "merge",
        }
    if "unrestricted_shared_files" not in work:
        work["unrestricted_shared_files"] = []
    if "consistency" not in work:
        work["consistency"] = {"checks": []}
    data["work"] = work

    # Ensure arc has all sub-keys
    arc = data.get("arc", {})
    if "no_test" not in arc.get("defaults", {}):
        arc.setdefault("defaults", {})["no_test"] = False
    if "consistency" not in arc:
        arc["consistency"] = {"checks": []}
    data["arc"] = arc

    # Ensure audit has all commented-out sub-keys
    audit = data.get("audit", {})
    if "incremental" not in audit:
        audit["incremental"] = {"enabled": False}
    if "dirs" not in audit:
        audit["dirs"] = None
    if "exclude_dirs" not in audit:
        audit["exclude_dirs"] = None
    data["audit"] = audit

    # Ensure echoes has all commented-out sub-keys
    echoes = data.get("echoes", {})
    if "fts_enabled" not in echoes:
        echoes["fts_enabled"] = True
    if "auto_observation" not in echoes:
        echoes["auto_observation"] = True
    data["echoes"] = echoes


if __name__ == "__main__":
    build_defaults()
