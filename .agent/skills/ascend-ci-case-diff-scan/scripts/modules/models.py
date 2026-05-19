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

"""Shared models and constants for the Ascend CI case diff scanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

UT_KIND = "ut"
ST_KIND = "st"
CASE_COMPARISON_SECTIONS = ("matched", "cpu_gpu_only", "npu_only", "manual_review")
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "workflow_scope.json"


@dataclass(frozen=True)
class WorkflowConfig:
    ignored_workflows: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowInfo:
    workflow_name: str
    workflow_path: str
    file_name: str
    workflow_kind: str
    pair_key: str
