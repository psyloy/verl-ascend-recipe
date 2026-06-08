# Ascend CI Case Diff Scan

Statically audit test-case coverage alignment between CPU/GPU and Ascend NPU CI workflows in a `verl` repository. See [SKILL.md](./SKILL.md) for the full skill reference.

## Quick start

```bash
python scripts/scan_ascend_ci_case_diff.py \
  --repo-root {PATH}/verl \
  --output-dir ./outputs

# With past-N-days incremental analysis
python scripts/scan_ascend_ci_case_diff.py \
  --repo-root {PATH}/verl \
  --output-dir ./outputs \
  --since-days 7
```

## Output

- `report.md` + `report.xlsx` — full audit (4 sheets: Ignored Workflows, Scanned Workflows, UT Cases, ST Cases)
- `report-past-N.md` + `report-past-N.xlsx` — incremental analysis (only when `--since-days` is set)

## Project structure

```
SKILL.md                  # Skill reference (loaded by Claude Code)
README.md                 # This file
config/workflow_scope.json # Ignored workflow patterns
references/repo-signals.md # Target-repo signal definitions
scripts/                  # Python scanner implementation
```
