"""Apply verl source patches required by true_on_policy (idempotent)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_PATCH_FILENAME = "verl_pr6678_pp_mindspeed.patch"
_ROLLOUT_CONFIG_REL = Path("verl/workers/config/rollout.py")


def _recipe_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _verl_root(recipe_dir: Path) -> Path:
    return recipe_dir.parent.parent


def _git_apply_check(verl_root: Path, patch_file: Path, *, reverse: bool = False) -> bool:
    cmd = ["git", "-C", str(verl_root), "apply"]
    if reverse:
        cmd.append("-R")
    cmd.extend(["--check", str(patch_file)])
    return subprocess.run(cmd, capture_output=True, check=False).returncode == 0


def apply_verl_source_patches() -> None:
    """Apply verl PR #6678 source patch on top of release/v0.8.0."""
    recipe_dir = _recipe_dir()
    verl_root = _verl_root(recipe_dir)
    patch_file = recipe_dir / "patch" / _PATCH_FILENAME
    rollout_config = verl_root / _ROLLOUT_CONFIG_REL

    if not patch_file.is_file():
        raise FileNotFoundError(f"[true_on_policy] patch file not found: {patch_file}")

    if not rollout_config.is_file():
        raise FileNotFoundError(
            f"[true_on_policy] verl source tree not found at {verl_root}; "
            "copy this recipe to verl/verl_ascend_recipe/true_on_policy first."
        )

    if _git_apply_check(verl_root, patch_file, reverse=True):
        return

    if not _git_apply_check(verl_root, patch_file):
        raise RuntimeError(
            f"[true_on_policy] patch does not apply cleanly under {verl_root}; "
            "ensure verl is checked out at release/v0.8.0."
        )

    subprocess.run(
        ["git", "-C", str(verl_root), "apply", str(patch_file)],
        check=True,
    )
    logger.warning(
        "[true_on_policy] applied %s (PR #6678 PP + MindSpeed repatch)",
        _PATCH_FILENAME,
    )
