"""Apply vLLM-Ascend source patches required by true_on_policy (idempotent)."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_BATCH_INVARIANT_REL = Path("vllm_ascend/batch_invariant.py")
_FA3_REL = Path("vllm_ascend/attention/fa3_v1.py")
_BATCH_INVARIANT_MARKER = "BatchInvariantSumFunction"
_FA3_MARKER = "AscendFABackend"
_VLLM_ASCEND_TRUE_ON_POLICY_PATCH = "vllm_ascend_true_on_policy.patch"


@dataclass
class VllmAscendPatchPlan:
    vllm_ascend_root: Path
    patch_files: list[Path] = field(default_factory=list)
    skip_reasons: list[str] = field(default_factory=list)


def _recipe_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _verl_root(recipe_dir: Path) -> Path:
    return recipe_dir.parent.parent


def _resolve_vllm_ascend_root(verl_root: Path) -> Path | None:
    env_root = os.environ.get("VLLM_ASCEND_ROOT", "").strip()
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root))
    candidates.append(verl_root.parent / "vllm-ascend")

    try:
        import vllm_ascend

        candidates.insert(0, Path(vllm_ascend.__file__).resolve().parent.parent)
    except ImportError:
        pass

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / _BATCH_INVARIANT_REL).is_file():
            return candidate
    return None


def _has_true_on_policy_vllm_ascend_patch(vllm_ascend_root: Path) -> bool:
    batch_invariant_text = (vllm_ascend_root / _BATCH_INVARIANT_REL).read_text(encoding="utf-8")
    if _BATCH_INVARIANT_MARKER not in batch_invariant_text:
        return False

    fa3_path = vllm_ascend_root / _FA3_REL
    if not fa3_path.is_file():
        return False

    fa3_text = fa3_path.read_text(encoding="utf-8")
    return _FA3_MARKER in fa3_text


def _git_apply_check(repo_root: Path, patch_file: Path, *, reverse: bool = False) -> bool:
    cmd = ["git", "-C", str(repo_root), "apply"]
    if reverse:
        cmd.append("-R")
    cmd.extend(["--check", str(patch_file)])
    return subprocess.run(cmd, capture_output=True, check=False).returncode == 0


def _apply_patch_file(repo_root: Path, patch_file: Path) -> None:
    if _git_apply_check(repo_root, patch_file, reverse=True):
        logger.info("[true_on_policy] vllm-ascend patch already applied: %s", patch_file.name)
        return

    if not _git_apply_check(repo_root, patch_file):
        raise RuntimeError(
            f"[true_on_policy] vllm-ascend patch does not apply cleanly: {patch_file.name} (tree at {repo_root})."
        )

    subprocess.run(
        ["git", "-C", str(repo_root), "apply", str(patch_file)],
        check=True,
    )
    logger.warning("[true_on_policy] applied vllm-ascend patch %s", patch_file.name)


def select_vllm_ascend_source_patches(recipe_dir: Path, vllm_ascend_root: Path) -> VllmAscendPatchPlan:
    plan = VllmAscendPatchPlan(vllm_ascend_root=vllm_ascend_root)
    patch_dir = recipe_dir / "patch" / "vllm_ascend_patches"

    if _has_true_on_policy_vllm_ascend_patch(vllm_ascend_root):
        plan.skip_reasons.append(
            "vllm-ascend already contains true_on_policy batch-invariant and FA3 backend patches"
        )
    else:
        plan.patch_files.append(patch_dir / _VLLM_ASCEND_TRUE_ON_POLICY_PATCH)

    return plan


def apply_vllm_ascend_source_patches() -> None:
    """Apply vLLM-Ascend source patches (batch_invariant + FA3 for train-infer consistency)."""
    recipe_dir = _recipe_dir()
    verl_root = _verl_root(recipe_dir)
    vllm_ascend_root = _resolve_vllm_ascend_root(verl_root)

    if vllm_ascend_root is None:
        logger.warning(
            "[true_on_policy] vllm-ascend source tree not found; "
            "set VLLM_ASCEND_ROOT or place vllm-ascend next to verl. Skipping vllm-ascend patches."
        )
        return

    plan = select_vllm_ascend_source_patches(recipe_dir, vllm_ascend_root)
    logger.info("[true_on_policy] vllm-ascend root: %s", plan.vllm_ascend_root)
    for reason in plan.skip_reasons:
        logger.info("[true_on_policy] %s", reason)

    if not plan.patch_files:
        logger.info("[true_on_policy] no vllm-ascend source patches needed")
        return

    for patch_file in plan.patch_files:
        _apply_patch_file(plan.vllm_ascend_root, patch_file)


def get_vllm_ascend_patch_plan() -> VllmAscendPatchPlan | None:
    recipe_dir = _recipe_dir()
    verl_root = _verl_root(recipe_dir)
    vllm_ascend_root = _resolve_vllm_ascend_root(verl_root)
    if vllm_ascend_root is None:
        return None
    return select_vllm_ascend_source_patches(recipe_dir, vllm_ascend_root)
