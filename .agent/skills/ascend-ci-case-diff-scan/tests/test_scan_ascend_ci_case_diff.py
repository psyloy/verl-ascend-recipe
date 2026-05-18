import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "scan_ascend_ci_case_diff.py"
SPEC = importlib.util.spec_from_file_location("scan_ascend_ci_case_diff", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_workflow(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


class ScanAscendCiCaseDiffTests(unittest.TestCase):
    def test_ignore_config_and_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            write_workflow(
                repo_root / ".github" / "workflows" / "docker-build-ascend-a2.yml",
                """
                name: Docker build
                jobs:
                  build:
                    steps:
                      - name: Build
                        run: bash tests/special_e2e/run_build.sh
                """,
            )
            write_workflow(
                repo_root / ".github" / "workflows" / "gpu_unit_tests.yml",
                """
                name: GPU unit tests
                jobs:
                  tests:
                    steps:
                      - name: Run GPU unit tests
                        run: pytest tests/foo/test_alpha.py
                """,
            )
            write_workflow(
                repo_root / ".github" / "workflows" / "npu_unit_tests.yml",
                """
                name: NPU unit tests
                runs-on: linux-aarch64-a2b3-8
                jobs:
                  tests:
                    steps:
                      - name: Run NPU unit tests
                        run: pytest tests/foo/test_alpha.py
                """,
            )
            (repo_root / "tests" / "foo").mkdir(parents=True, exist_ok=True)
            (repo_root / "tests" / "foo" / "test_alpha.py").write_text("def test_alpha():\n    pass\n", encoding="utf-8")

            config = MODULE.load_config()
            workflow_infos, cases, ignored_paths = MODULE.collect_scan_data(repo_root, config)

            self.assertEqual(ignored_paths, [".github/workflows/docker-build-ascend-a2.yml"])
            pair_keys = {info.file_name: info.pair_key for info in workflow_infos}
            self.assertEqual(pair_keys["gpu_unit_tests.yml"], "gpu_unit_tests")
            self.assertEqual(pair_keys["npu_unit_tests.yml"], "gpu_unit_tests")
            self.assertEqual(len(cases), 2)

    def test_ut_directory_expansion_and_step_disambiguation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            write_workflow(
                repo_root / ".github" / "workflows" / "gpu_unit_tests.yml",
                """
                name: GPU unit tests
                jobs:
                  tests:
                    steps:
                      - name: UT one
                        run: pytest tests/
                      - name: UT two
                        run: pytest tests/
                """,
            )
            (repo_root / "tests" / "trainer" / "ppo").mkdir(parents=True, exist_ok=True)
            (repo_root / "tests" / "trainer" / "ppo" / "test_core.py").write_text("def test_core():\n    pass\n", encoding="utf-8")
            (repo_root / "tests" / "trainer" / "ppo" / "test_other.py").write_text("def test_other():\n    pass\n", encoding="utf-8")

            config = MODULE.load_config()
            _, cases, _ = MODULE.collect_scan_data(repo_root, config)
            ut_cases = [case for case in cases if case["case_kind"] == MODULE.UT_KIND]

            self.assertEqual(len(ut_cases), 4)
            case_ids = {case["case_id"] for case in ut_cases}
            self.assertEqual(len(case_ids), 4)
            targets = sorted({case["target"] for case in ut_cases})
            self.assertEqual(
                targets,
                [
                    "tests/trainer/ppo/test_core.py",
                    "tests/trainer/ppo/test_other.py",
                ],
            )

    def test_st_command_disambiguation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            write_workflow(
                repo_root / ".github" / "workflows" / "model.yml",
                """
                name: Model
                jobs:
                  tests:
                    steps:
                      - name: ST one
                        run: bash tests/special_e2e/run_model.sh
                      - name: ST two
                        run: bash tests/special_e2e/run_model.sh
                """,
            )
            config = MODULE.load_config()
            _, cases, _ = MODULE.collect_scan_data(repo_root, config)
            st_cases = [case for case in cases if case["case_kind"] == MODULE.ST_KIND]

            self.assertEqual(len(st_cases), 2)
            self.assertEqual(len({case["case_id"] for case in st_cases}), 2)

    def test_st_same_step_multiple_commands_keep_distinct_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            write_workflow(
                repo_root / ".github" / "workflows" / "e2e_sft_llm_ascend.yml",
                """
                name: e2e_sft_llm_ascend
                runs-on: linux-aarch64-a2b3-8
                jobs:
                  tests:
                    steps:
                      - name: multiturn
                        run: |
                          BACKEND=fsdp bash tests/special_e2e/sft/run_sft_engine.sh
                          BACKEND=veomni bash tests/special_e2e/sft/run_sft_engine.sh
                """,
            )
            config = MODULE.load_config()
            _, cases, _ = MODULE.collect_scan_data(repo_root, config)
            st_cases = [case for case in cases if case["case_kind"] == MODULE.ST_KIND]

            self.assertEqual(len(st_cases), 2)
            self.assertEqual(len({case["case_id"] for case in st_cases}), 2)
            self.assertEqual(len({case["line_number"] for case in st_cases}), 2)

    def test_ut_directory_and_single_file_do_not_align(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            write_workflow(
                repo_root / ".github" / "workflows" / "gpu_unit_tests.yml",
                """
                name: GPU unit tests
                jobs:
                  tests:
                    steps:
                      - name: Run all GPU unit tests
                        run: pytest tests/
                """,
            )
            write_workflow(
                repo_root / ".github" / "workflows" / "npu_unit_tests.yml",
                """
                name: NPU unit tests
                runs-on: linux-aarch64-a2b3-8
                jobs:
                  tests:
                    steps:
                      - name: Testing normalize peft param name
                        run: pytest tests/utils/test_normalize_peft_param_name.py
                """,
            )
            (repo_root / "tests" / "utils").mkdir(parents=True, exist_ok=True)
            (repo_root / "tests" / "utils" / "test_normalize_peft_param_name.py").write_text(
                "def test_normalize_peft_param_name():\n    pass\n",
                encoding="utf-8",
            )

            config = MODULE.load_config()
            report = MODULE.build_report(repo_root, config)

            matched_names = {item["name"] for item in report["ut_details"]["matched"]}
            manual_names = {item["name"] for item in report["ut_details"]["manual_review"]}
            self.assertNotIn("tests/utils/test_normalize_peft_param_name.py", matched_names)
            self.assertIn("tests/utils/test_normalize_peft_param_name.py", manual_names)


if __name__ == "__main__":
    unittest.main()
