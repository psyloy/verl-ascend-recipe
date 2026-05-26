# Ascend CI Case Diff Scan

This skill statically audits a target `verl` repository and reports workflow/case alignment between CPU/GPU and NPU workflows.

## What it does

- Excludes non-test and non-comparable workflows through `config/workflow_scope.json`
- Pairs CPU/GPU workflows with their NPU counterparts
- Counts UT cases at the test-function or test-method level
- Counts ST cases at the command level
- Writes English `report.md` and `report.xlsx` files
- Optionally writes `report-past-N.md` and `report-past-N.xlsx` for recent merged commits when `--since-days N` is set

## Workflow pairing

- `foo.yml` pairs with `foo_ascend.yml`
- `gpu_unit_tests.yml` pairs with `npu_unit_tests.yml`
- Standalone NPU workflows such as `e2e_ascend.yml` and `nightly_ascend.yml` remain NPU-only

## Case rules

- `pytest` means UT
- UT entries are expanded to concrete test functions or test methods whenever the target Python file can be parsed
- `torchrun`, `bash tests/*.sh`, and `bash examples/*.sh` mean ST
- Repeated commands are kept distinct by `workflow name`, `job name`, and `step name`
- Use `--repo-root` to point at the target `verl` repository root
- The scanner reads workflow `run:` commands directly and records only the scripts explicitly invoked by each step
- `--since-days` enables a second report that traces the final workflow / UT / ST changes within the selected window and checks them against the current HEAD NPU support state
- The past-N-days report keeps the same workflow-first logic as the full scan, but only surfaces workflows and cases that actually changed within the window

## Output

The reports include:

- ignored workflows
- scanned workflows with CPU/GPU and NPU case counts
- UT details
- ST details

Within UT and ST sections, the report shows matched, CPU/GPU-only, NPU-only, and manual-review cases in that order, with adjacent CPU/GPU and NPU references for easy comparison.

The Excel workbook contains four sheets: `Ignored Workflows`, `Scanned Workflows`, `UT Cases`, and `ST Cases`.

The past-N-days workbook contains summary, changed-workflow, changed-case, and commit-detail sheets.
