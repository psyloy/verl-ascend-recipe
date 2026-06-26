"""true_on_policy patch entry — loaded via VERL_USE_EXTERNAL_MODULES on import verl."""

from .apply_verl_source_patches import apply_verl_source_patches
from .npu_true_on_policy_patch import apply_batch_consistency_patches

# Source patches must land before importing patched verl rollout modules.
apply_verl_source_patches()
apply_batch_consistency_patches()
