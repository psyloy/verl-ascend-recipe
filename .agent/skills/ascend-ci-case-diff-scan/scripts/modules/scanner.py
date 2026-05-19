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

"""Top-level report assembly."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from .compare import compare_cases_by_pair, summarize_scanned_workflows
from .models import ST_KIND, UT_KIND, WorkflowConfig
from .workflows import build_workflow_groups, collect_scan_data


def build_report(repo_root: Path, config: WorkflowConfig) -> dict:
    """Build the in-memory report data."""
    workflow_infos, cases, ignored_paths = collect_scan_data(repo_root, config)
    grouped_workflows = build_workflow_groups(workflow_infos)
    return {
        "repo_root": str(repo_root),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ignored_workflows": ignored_paths,
        "scanned_workflows": summarize_scanned_workflows(grouped_workflows, cases),
        "ut_details": compare_cases_by_pair(cases, UT_KIND),
        "st_details": compare_cases_by_pair(cases, ST_KIND),
    }
