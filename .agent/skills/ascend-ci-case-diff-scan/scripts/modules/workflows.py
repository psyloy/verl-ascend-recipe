#!/usr/bin/env python3
# Copyright 2025 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workflow parsing and scan collection."""

from __future__ import annotations

import re
from pathlib import Path

from .config import is_ignored_workflow, load_text
from .extractors import (
    expand_pytest_targets,
    extract_bash_target,
    extract_pytest_ignore_specs,
    extract_pytest_targets,
    extract_torchrun_targets,
    should_keep_target,
)
from .models import ST_KIND, UT_KIND, WorkflowConfig, WorkflowInfo
from .shell import (
    command_uses_pytest,
    command_uses_torchrun,
    normalize_path_text,
    normalize_signature,
    split_shell_commands,
    tokenize_command,
)

WORKFLOW_NAME_RE = re.compile(r"^\s*name:\s*(.+?)\s*$")
JOB_RE = re.compile(r"^(\s{2})([A-Za-z0-9_-]+):\s*$")
STEP_NAME_RE = re.compile(r"^(\s*)-\s+name:\s*(.+?)\s*$")
RUN_RE = re.compile(r"^(\s*)run:\s*(.*)$")
RUNS_ON_ASCEND_RE = re.compile(r"runs-on:\s+.*(?:aarch64|a2|a3)", re.IGNORECASE)
IMAGE_ASCEND_RE = re.compile(r"image:\s+.*ascend", re.IGNORECASE)


def classify_workflow(file_stem: str, content: str) -> str:
    """Classify workflows into cpu, gpu, or npu buckets."""
    stem = file_stem.lower()
    if stem == "cpu_unit_tests":
        return "cpu"
    if stem == "npu_unit_tests" or stem.endswith("_ascend") or "nightly_ascend" in stem:
        return "npu"
    if RUNS_ON_ASCEND_RE.search(content) or IMAGE_ASCEND_RE.search(content):
        return "npu"
    return "gpu"


def workflow_pair_key(file_stem: str) -> str:
    """Map workflow file names into CPU/GPU vs NPU pairing groups."""
    stem = file_stem.lower()
    if stem == "npu_unit_tests":
        return "gpu_unit_tests"
    if stem.endswith("_ascend"):
        return stem[: -len("_ascend")]
    return stem


def build_case_id(case: dict) -> str:
    """Build a per-occurrence case key that preserves workflow/job/step distinctions."""
    return "|".join(
        [
            case["case_kind"],
            case["command_type"],
            case["target"],
            case["signature"],
            case["workflow_name"],
            case["job_name"],
            case["step_name"],
            str(case["line_number"]),
        ]
    )


def build_display_name(case: dict) -> str:
    """Produce the report-facing case name for UT and ST entries."""
    if case["case_kind"] == UT_KIND:
        return case["target"]
    return f"{case['target']} [{case['workflow_name']} / {case['job_name']} / {case['step_name']}]"


def _extract_run_entries(lines: list[str], start_idx: int, indent: int, inline: str) -> tuple[list[tuple[str, int]], int]:
    run_entries: list[tuple[str, int]] = []
    if inline and inline not in {"|", ">"}:
        run_entries.append((inline, start_idx + 1))
    idx = start_idx + 1
    while idx < len(lines):
        next_line = lines[idx]
        next_indent = len(next_line) - len(next_line.lstrip(" "))
        if next_line.strip() == "":
            idx += 1
            continue
        if next_indent <= indent:
            break
        stripped = next_line[indent + 2 :] if len(next_line) >= indent + 2 else next_line.lstrip()
        run_entries.append((stripped, idx + 1))
        idx += 1
    return run_entries, idx


def _expand_case_record(
    case: dict,
    workflow_info: WorkflowInfo,
    file_name: str,
    job_name: str,
    step_name: str,
    line_number: int,
    workflow_kind: str,
) -> list[dict]:
    expanded_cases: list[dict] = []
    for target in case["targets"]:
        expanded_case = {
            "workflow_name": workflow_info.workflow_name,
            "workflow_path": workflow_info.workflow_path,
            "file_name": file_name,
            "workflow_kind": workflow_kind,
            "pair_key": workflow_info.pair_key,
            "job_name": job_name,
            "step_name": step_name,
            "line_number": line_number,
            "command_type": case["command_type"],
            "case_kind": case["case_kind"],
            "target": target,
            "raw_command": case["raw_command"],
            "signature": case["signature"],
        }
        expanded_case["case_id"] = build_case_id(expanded_case)
        expanded_case["display_name"] = build_display_name(expanded_case)
        expanded_cases.append(expanded_case)
    return expanded_cases


def _extract_cases_from_command(
    command: str,
    repo_root: Path,
) -> list[dict]:
    command = command.strip()
    if not command or command.startswith("#"):
        return []

    tokens = tokenize_command(command)
    if not tokens:
        return []

    cases: list[dict] = []
    bash_target = extract_bash_target(tokens)
    if bash_target and should_keep_target(bash_target, "bash"):
        cases.append(
            {
                "command_type": "bash",
                "case_kind": ST_KIND,
                "target": bash_target,
                "targets": [bash_target],
                "raw_command": command,
                "signature": normalize_signature(command, bash_target),
            }
        )

    if command_uses_torchrun(command, tokens):
        torchrun_idx = tokens.index("torchrun") if "torchrun" in tokens else 0
        for target in extract_torchrun_targets(tokens, torchrun_idx):
            if not should_keep_target(target, "torchrun"):
                continue
            cases.append(
                {
                    "command_type": "torchrun",
                    "case_kind": ST_KIND,
                    "target": target,
                    "targets": [target],
                    "raw_command": command,
                    "signature": normalize_signature(command, target),
                }
            )
    elif command_uses_pytest(tokens):
        pytest_idx = tokens.index("pytest")
        ignore_paths, ignore_globs = extract_pytest_ignore_specs(tokens, pytest_idx)
        for target in extract_pytest_targets(tokens, pytest_idx):
            if not should_keep_target(target, "pytest"):
                continue
            normalized_target = normalize_path_text(target)
            if normalized_target in {"tests", "tests/"} or Path(normalized_target).suffix == "":
                target_shape = "pytest-dir"
            elif normalized_target.endswith(".py"):
                target_shape = "pytest-file"
            else:
                target_shape = "pytest-target"

            signature = normalize_signature(command, target)
            if signature:
                signature = f"{signature} {target_shape}"
            else:
                signature = target_shape

            cases.append(
                {
                    "command_type": "pytest",
                    "case_kind": UT_KIND,
                    "target": target,
                    "targets": expand_pytest_targets(
                        target,
                        repo_root,
                        ignore_paths,
                        ignore_globs,
                    ),
                    "raw_command": command,
                    "signature": signature,
                }
            )

    deduped: list[dict] = []
    seen = set()
    for case in cases:
        key = (case["command_type"], tuple(case["targets"]), case["signature"], case["raw_command"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(case)
    return deduped


def parse_workflow(path: Path, repo_root: Path, config: WorkflowConfig) -> tuple[WorkflowInfo | None, list[dict]]:
    """Parse one workflow file and extract test cases from each run block."""
    file_name = path.name
    if is_ignored_workflow(file_name, config):
        return None, []

    content = load_text(path)
    workflow_name = path.stem
    name_match = WORKFLOW_NAME_RE.search(content)
    if name_match:
        workflow_name = name_match.group(1).strip().strip("\"'")
    workflow_kind = classify_workflow(path.stem, content)
    workflow_info = WorkflowInfo(
        workflow_name=workflow_name,
        workflow_path=normalize_path_text(path.relative_to(repo_root).as_posix()),
        file_name=file_name,
        workflow_kind=workflow_kind,
        pair_key=workflow_pair_key(path.stem),
    )

    lines = content.splitlines()
    job_name = "unknown"
    step_name = "(unnamed step)"
    cases: list[dict] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        job_match = JOB_RE.match(line)
        if job_match:
            job_name = job_match.group(2)
        step_match = STEP_NAME_RE.match(line)
        if step_match:
            step_name = step_match.group(2).strip()
        run_match = RUN_RE.match(line)
        if run_match:
            indent = len(run_match.group(1))
            run_entries, next_idx = _extract_run_entries(lines, idx, indent, run_match.group(2).strip())
            for raw, line_number in run_entries:
                for command in split_shell_commands(raw):
                    for case in _extract_cases_from_command(command, repo_root):
                        cases.extend(
                            _expand_case_record(
                                case,
                                workflow_info,
                                file_name,
                                job_name,
                                step_name,
                                line_number,
                                workflow_kind,
                            )
                        )
            idx = next_idx
            continue
        idx += 1
    return workflow_info, cases


def collect_scan_data(repo_root: Path, config: WorkflowConfig) -> tuple[list[WorkflowInfo], list[dict], list[str]]:
    """Scan workflows and return parsed workflow metadata, cases, and ignored paths."""
    workflow_dir = repo_root / ".github" / "workflows"
    workflow_infos: list[WorkflowInfo] = []
    cases: list[dict] = []
    ignored_paths: list[str] = []
    for path in sorted(workflow_dir.glob("*.yml")):
        rel_path = normalize_path_text(path.relative_to(repo_root).as_posix())
        if is_ignored_workflow(path.name, config):
            ignored_paths.append(rel_path)
            continue
        workflow_info, workflow_cases = parse_workflow(path, repo_root, config)
        if workflow_info is None:
            ignored_paths.append(rel_path)
            continue
        workflow_infos.append(workflow_info)
        cases.extend(workflow_cases)
    return workflow_infos, cases, ignored_paths


def build_workflow_groups(workflow_infos: list[WorkflowInfo]) -> dict[str, dict[str, list[WorkflowInfo]]]:
    """Group workflows by their CPU/GPU vs NPU pairing key."""
    grouped: dict[str, dict[str, list[WorkflowInfo]]] = {}
    for info in workflow_infos:
        side = "npu" if info.workflow_kind == "npu" else "cpu_gpu"
        grouped.setdefault(info.pair_key, {"cpu_gpu": [], "npu": []})[side].append(info)
    return grouped
