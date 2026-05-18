[1mdiff --git a/.agent/skills/ascend-ci-case-diff-scan/scripts/scan_ascend_ci_case_diff.py b/.agent/skills/ascend-ci-case-diff-scan/scripts/scan_ascend_ci_case_diff.py[m
[1mindex c112221..ad81f13 100644[m
[1m--- a/.agent/skills/ascend-ci-case-diff-scan/scripts/scan_ascend_ci_case_diff.py[m
[1m+++ b/.agent/skills/ascend-ci-case-diff-scan/scripts/scan_ascend_ci_case_diff.py[m
[36m@@ -26,7 +26,6 @@[m [mfrom collections import Counter, defaultdict[m
 from itertools import zip_longest[m
 from pathlib import Path[m
 [m
[31m-[m
 IGNORED_WORKFLOW_NAMES = {[m
     "check-pr-title",[m
     "doc",[m
[36m@@ -453,15 +452,9 @@[m [mdef compare_case_sets(cpu_gpu_cases: list[dict], npu_cases: list[dict]) -> list[[m
         npu_only_signatures = sorted(set(npu_by_signature) - set(baseline_by_signature))[m
         if baseline_only_signatures or npu_only_signatures:[m
             unmatched_baseline_cases = [[m
[31m-                case[m
[31m-                for signature in baseline_only_signatures[m
[31m-                for case in baseline_by_signature[signature][m
[31m-            ][m
[31m-            unmatched_npu_cases = [[m
[31m-                case[m
[31m-                for signature in npu_only_signatures[m
[31m-                for case in npu_by_signature[signature][m
[32m+[m[32m                case for signature in baseline_only_signatures for case in baseline_by_signature[signature][m
             ][m
[32m+[m[32m            unmatched_npu_cases = [case for signature in npu_only_signatures for case in npu_by_signature[signature]][m
             items.append([m
                 {[m
                     "id": stable_id([m
[36m@@ -480,9 +473,7 @@[m [mdef compare_case_sets(cpu_gpu_cases: list[dict], npu_cases: list[dict]) -> list[[m
                             format_signature_summary("baseline-only", baseline_only_signatures)[m
                             if baseline_only_signatures[m
                             else "",[m
[31m-                            format_signature_summary("npu-only", npu_only_signatures)[m
[31m-                            if npu_only_signatures[m
[31m-                            else "",[m
[32m+[m[32m                            format_signature_summary("npu-only", npu_only_signatures) if npu_only_signatures else "",[m
                         )[m
                         if part[m
                     ),[m
[36m@@ -553,9 +544,7 @@[m [mdef render_reference_details(indent: str, label: str, ref: dict | None) -> list[[m
         return lines[m
     lines.append(f"{indent}  - Workflow file: `{ref['workflow_path']}`")[m
     lines.append(f"{indent}  - Line: `{ref['line_number']}`")[m
[31m-    lines.append([m
[31m-        f"{indent}  - Workflow context: `{ref['workflow_name']} / {ref['job_name']} / {ref['step_name']}`"[m
[31m-    )[m
[32m+[m[32m    lines.append(f"{indent}  - Workflow context: `{ref['workflow_name']} / {ref['job_name']} / {ref['step_name']}`")[m
     lines.append(f"{indent}  - Command: `{ref['raw_command']}`")[m
     return lines[m
 [m
[36m@@ -644,16 +633,13 @@[m [mdef validate_repo_root(repo_root: Path) -> None:[m
     workflow_dir = repo_root / ".github" / "workflows"[m
     if not workflow_dir.is_dir():[m
         raise FileNotFoundError([m
[31m-            "Target repository does not contain '.github/workflows'. "[m
[31m-            f"Expected workflow directory: {workflow_dir}"[m
[32m+[m[32m            f"Target repository does not contain '.github/workflows'. Expected workflow directory: {workflow_dir}"[m
         )[m
 [m
 [m
 def main() -> int:[m
     """CLI entrypoint for running the workflow parity scan."""[m
[31m-    parser = argparse.ArgumentParser([m
[31m-        description="Scan Ascend CI case differences for a target verl repository."[m
[31m-    )[m
[32m+[m[32m    parser = argparse.ArgumentParser(description="Scan Ascend CI case differences for a target verl repository.")[m
     parser.add_argument([m
         "--repo-root",[m
         "--target-repo-root",[m
