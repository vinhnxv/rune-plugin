"""Unit tests for resolve-session-identity.sh.

Tests the sourced identity resolver that exports RUNE_CURRENT_CFG.
Verifies config dir resolution, symlink handling, caching, and fallbacks.

Note: This script is meant to be `source`d, not executed directly.
We test it by wrapping it in a bash snippet that sources and prints RUNE_CURRENT_CFG.
"""

from __future__ import annotations

import os
import subprocess

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "resolve-session-identity.sh"


def run_identity(
    *,
    config_dir: str | None = None,
    pre_set_cfg: str | None = None,
    env_override: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Source resolve-session-identity.sh and print RUNE_CURRENT_CFG."""
    # Build a bash snippet that sources the script and prints the result
    parts = []
    if pre_set_cfg is not None:
        parts.append(f'export RUNE_CURRENT_CFG="{pre_set_cfg}"')
    parts.append(f'source "{SCRIPT}"')
    parts.append('echo "$RUNE_CURRENT_CFG"')
    snippet = "\n".join(parts)
    env = os.environ.copy()
    if config_dir is not None:
        env["CLAUDE_CONFIG_DIR"] = config_dir
    else:
        env.pop("CLAUDE_CONFIG_DIR", None)
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", "-c", snippet],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


# ---------------------------------------------------------------------------
# Basic Resolution
# ---------------------------------------------------------------------------


class TestResolveSessionIdentity:
    def test_resolves_custom_config_dir(self, tmp_path):
        """CLAUDE_CONFIG_DIR is resolved to absolute path."""
        config = tmp_path / "custom-config"
        config.mkdir()
        result = run_identity(config_dir=str(config))
        assert result.returncode == 0
        resolved = result.stdout.strip()
        assert resolved != ""
        # Should be an absolute path
        assert resolved.startswith("/")

    def test_resolves_symlinks(self, tmp_path):
        """Symlinked config dir is resolved to real path."""
        real_dir = tmp_path / "real-config"
        real_dir.mkdir()
        link = tmp_path / "link-config"
        link.symlink_to(real_dir)
        result = run_identity(config_dir=str(link))
        assert result.returncode == 0
        resolved = result.stdout.strip()
        # pwd -P resolves symlinks
        assert "link-config" not in resolved
        assert "real-config" in resolved

    def test_falls_back_to_home_claude(self):
        """Without CLAUDE_CONFIG_DIR, falls back to $HOME/.claude."""
        result = run_identity(config_dir=None)
        assert result.returncode == 0
        resolved = result.stdout.strip()
        assert resolved != ""
        # Should contain .claude
        assert ".claude" in resolved

    def test_caches_on_second_source(self, tmp_path):
        """If RUNE_CURRENT_CFG is already set, it is not re-resolved."""
        config = tmp_path / "config"
        config.mkdir()
        result = run_identity(
            config_dir=str(config),
            pre_set_cfg="/already/set/path",
        )
        assert result.returncode == 0
        resolved = result.stdout.strip()
        assert resolved == "/already/set/path"

    def test_nonexistent_config_dir_uses_literal(self):
        """If CLAUDE_CONFIG_DIR doesn't exist, uses the literal path."""
        result = run_identity(config_dir="/nonexistent/path/config")
        assert result.returncode == 0
        resolved = result.stdout.strip()
        # cd fails, falls back to echo of the original path
        assert resolved == "/nonexistent/path/config"

    def test_exports_variable(self, tmp_path):
        """RUNE_CURRENT_CFG is exported (available to subshells)."""
        config = tmp_path / "config"
        config.mkdir()
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config)
        result = subprocess.run(
            ["bash", "-c", f'source "{SCRIPT}" && bash -c \'echo "$RUNE_CURRENT_CFG"\''],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() != ""
