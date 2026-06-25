"""Apply verl source patches required by true_on_policy (idempotent, version-aware)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from .verl_patch_selector import VerlPatchPlan, select_verl_source_patches

logger = logging.getLogger(__name__)

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


def _apply_patch_file(verl_root: Path, patch_file: Path) -> None:
    if _git_apply_check(verl_root, patch_file, reverse=True):
        logger.info("[true_on_policy] patch already applied: %s", patch_file.name)
        return

    if not _git_apply_check(verl_root, patch_file):
        raise RuntimeError(
            f"[true_on_policy] patch does not apply cleanly: {patch_file.name} "
            f"(verl tree at {verl_root})."
        )

    subprocess.run(
        ["git", "-C", str(verl_root), "apply", str(patch_file)],
        check=True,
    )
    logger.warning("[true_on_policy] applied %s", patch_file.name)


def apply_verl_source_patches() -> None:
    """Apply version-selected verl source patches (PR #6732 PP + MindSpeed batch-invariant)."""
    recipe_dir = _recipe_dir()
    verl_root = _verl_root(recipe_dir)
    rollout_config = verl_root / _ROLLOUT_CONFIG_REL

    if not rollout_config.is_file():
        raise FileNotFoundError(
            f"[true_on_policy] verl source tree not found at {verl_root}; "
            "copy this recipe to verl/verl_ascend_recipe/true_on_policy first."
        )

    plan = select_verl_source_patches(recipe_dir, verl_root)
    logger.info(
        "[true_on_policy] detected verl %s (%s)",
        plan.verl_version,
        plan.verl_branch,
    )
    for reason in plan.skip_reasons:
        logger.info("[true_on_policy] %s", reason)

    if not plan.patch_files:
        logger.info("[true_on_policy] no verl source patches needed")
        return

    for patch_file in plan.patch_files:
        _apply_patch_file(verl_root, patch_file)


def get_verl_patch_plan() -> VerlPatchPlan:
    """Return the patch plan for the current verl tree (for diagnostics/tests)."""
    recipe_dir = _recipe_dir()
    verl_root = _verl_root(recipe_dir)
    return select_verl_source_patches(recipe_dir, verl_root)
