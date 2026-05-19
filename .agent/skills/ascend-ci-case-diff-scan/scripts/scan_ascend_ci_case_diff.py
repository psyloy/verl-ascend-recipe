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

"""CLI entrypoint for scanning workflow-level Ascend CI case differences."""

from __future__ import annotations

import argparse
from pathlib import Path

from modules.config import load_config, validate_repo_root
from modules.render import render_report
from modules.scanner import build_report


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Scan Ascend CI case differences for a target verl repository.")
    parser.add_argument(
        "--repo-root",
        "--target-repo-root",
        dest="repo_root",
        required=True,
        help="Path to the target verl repository root to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the generated report.md will be written.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the workflow parity scan."""
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    validate_repo_root(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()
    report = build_report(repo_root, config)
    report_path = output_dir / "report.md"
    report_path.write_text(render_report(report), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
