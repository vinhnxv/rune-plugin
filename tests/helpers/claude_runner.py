"""Claude CLI subprocess wrapper for automated /rune:arc invocation.

Invokes `claude -p` in non-interactive mode with the Rune plugin loaded,
captures structured JSON output, and tracks token usage and timing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunResult:
    """Result from a Claude CLI invocation."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    output_json: dict | None = None
    session_id: str | None = None
    token_usage: dict | None = None

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def result_text(self) -> str:
        if self.output_json and "result" in self.output_json:
            return self.output_json["result"]
        return self.stdout


@dataclass
class ClaudeRunner:
    """Wrapper for invoking Claude Code CLI as a subprocess.

    Configures isolated execution with:
    - Rune plugin loaded via --plugin-dir
    - No memory persistence (CLAUDE_CODE_DISABLE_AUTO_MEMORY=1)
    - Structured JSON output for machine parsing
    - Cost and turn limits for safety
    """

    plugin_dir: Path
    working_dir: Path
    max_turns: int = 200
    max_budget_usd: float = 15.0
    timeout_seconds: int = 3600  # 60 min default
    model: str | None = None
    extra_env: dict[str, str] = field(default_factory=dict)
    verbose: bool = False
    isolated_config_dir: Path | None = None

    # Fixed isolated config location in user home
    CONFIG_DIR_NAME = ".claude-rune-plugin-test"
    # Auth files to preserve from real ~/.claude/ when isolating
    _AUTH_FILES = ("settings.json", "settings.local.json")
    # State dirs to create fresh in isolated config
    _STATE_DIRS = ("teams", "tasks", "projects", "agent-memory")

    @classmethod
    def default_config_dir(cls) -> Path:
        """Return the fixed isolated config path: ~/.claude-rune-plugin-test/"""
        return Path.home() / cls.CONFIG_DIR_NAME

    def setup_isolated_config(self) -> Path:
        """Create isolated Claude config dir at ~/.claude-rune-plugin-test/.

        Wipes and recreates the directory each time for a clean slate:
        - Auth files copied from ~/.claude/ (settings.json, settings.local.json)
        - Empty state directories (teams/, tasks/, projects/, agent-memory/)

        This ensures each E2E run starts fresh for Agent Teams,
        arc checkpoints, and agent memory — without losing auth.
        """
        config_dir = self.default_config_dir()
        if config_dir.exists():
            shutil.rmtree(config_dir)
        config_dir.mkdir()

        # Preserve auth from real config
        real_config = Path.home() / ".claude"
        for auth_file in self._AUTH_FILES:
            src = real_config / auth_file
            if src.exists():
                shutil.copy2(src, config_dir / auth_file)

        # Create empty state dirs so Claude doesn't fail on missing paths
        for subdir in self._STATE_DIRS:
            (config_dir / subdir).mkdir(exist_ok=True)

        self.isolated_config_dir = config_dir
        return config_dir

    def cleanup_config(self) -> None:
        """Wipe the isolated config directory contents (keeps the dir)."""
        if self.isolated_config_dir and self.isolated_config_dir.exists():
            shutil.rmtree(self.isolated_config_dir, ignore_errors=True)
            self.isolated_config_dir = None

    def _build_env(self) -> dict[str, str]:
        """Build isolated environment for Claude CLI."""
        env = os.environ.copy()
        # Disable memory and telemetry for hermetic testing
        env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
        env["DISABLE_TELEMETRY"] = "1"
        env["DISABLE_ERROR_REPORTING"] = "1"
        env["DISABLE_AUTOUPDATER"] = "1"
        env["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] = "1"
        # Enable Agent Teams (required for Rune)
        env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

        # Redirect config directory for full state isolation
        if self.isolated_config_dir:
            env["CLAUDE_CONFIG_DIR"] = str(self.isolated_config_dir)

        # Remove CLAUDECODE marker so nested invocation works
        env.pop("CLAUDECODE", None)

        env.update(self.extra_env)
        return env

    def _build_args(self, prompt: str) -> list[str]:
        """Build claude CLI argument list."""
        args = [
            "claude",
            "-p", prompt,
            "--plugin-dir", str(self.plugin_dir.resolve()),
            "--output-format", "json",
            "--no-session-persistence",
            "--max-turns", str(self.max_turns),
            "--dangerously-skip-permissions",
        ]
        if self.model:
            args.extend(["--model", self.model])
        if self.verbose:
            args.append("--verbose")
        return args

    def run(self, prompt: str) -> RunResult:
        """Execute a single prompt and return structured result."""
        args = self._build_args(prompt)
        env = self._build_env()

        start = time.monotonic()
        try:
            proc = subprocess.run(
                args,
                cwd=self.working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as e:
            duration = time.monotonic() - start
            return RunResult(
                exit_code=-1,
                stdout=(e.stdout or b"").decode(errors="replace"),
                stderr=f"TIMEOUT after {duration:.0f}s",
                duration_seconds=duration,
            )

        duration = time.monotonic() - start

        # Parse JSON output
        output_json = None
        session_id = None
        token_usage = None
        try:
            output_json = json.loads(proc.stdout)
            session_id = output_json.get("session_id")
            token_usage = output_json.get("usage")
        except (json.JSONDecodeError, TypeError):
            pass

        return RunResult(
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_seconds=duration,
            output_json=output_json,
            session_id=session_id,
            token_usage=token_usage,
        )

    def run_arc(
        self,
        plan_file: str,
        flags: list[str] | None = None,
    ) -> RunResult:
        """Run /rune:arc with a plan file.

        Args:
            plan_file: Relative path to plan file from working_dir.
            flags: Additional flags like --no-forge, --approve.
        """
        flag_str = " ".join(flags) if flags else ""
        prompt = f"/rune:arc {plan_file} {flag_str}".strip()
        return self.run(prompt)

    def run_review(self) -> RunResult:
        """Run /rune:review on current changes."""
        return self.run("/rune:review")

    def run_command(self, command: str) -> RunResult:
        """Run any /rune: command."""
        return self.run(command)
