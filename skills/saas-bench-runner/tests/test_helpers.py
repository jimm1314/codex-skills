from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _runlib import inspect_run, redact, status_fingerprint  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class RunHelpersTest(unittest.TestCase):
    def test_redact_hides_secret_assignments(self) -> None:
        text = redact("API_KEY=secret Authorization:Bearer abc.def TOKEN: xyz")
        self.assertNotIn("secret", text)
        self.assertNotIn("abc.def", text)
        self.assertNotIn("xyz", text)
        self.assertIn("<redacted>", text)

    def test_harbor_agent_error_is_visible_even_with_reward(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            write_json(
                run_dir / "result.json",
                {
                    "finished_at": "2026-01-01T01:00:00Z",
                    "n_total_trials": 1,
                    "stats": {
                        "n_completed_trials": 1,
                        "n_errored_trials": 0,
                        "n_running_trials": 0,
                        "n_pending_trials": 0,
                        "n_cancelled_trials": 0,
                    },
                },
            )
            trial = run_dir / "agriculture_022__trial"
            write_json(
                trial / "config.json",
                {
                    "task": {"path": "datasets/saas-bench/agriculture_022"},
                    "agent": {"model_name": "model", "kwargs": {"max_steps": 400}},
                    "verifier": {"kwargs": {}},
                },
            )
            write_json(
                trial / "result.json",
                {
                    "task_name": "saas-bench/agriculture_022",
                    "finished_at": "2026-01-01T01:00:00Z",
                    "agent_result": {"metadata": {"saas_bench": {"status": "error"}}},
                    "verifier_result": {"rewards": {"reward": 0.357}},
                },
            )
            write_json(
                trial / "agent" / "saas_bench_result.json",
                {"status": "error", "error_steps": ["env: /state -> browser_dead"]},
            )
            write_json(
                trial / "verifier" / "saas_bench_verify.json",
                {"status": "FAIL", "score": 0.357, "checks": []},
            )

            snapshot = inspect_run(run_dir, "auto")

            self.assertTrue(snapshot["terminal"])
            self.assertEqual(snapshot["trials"][0]["agent_status"], "error")
            self.assertEqual(snapshot["trials"][0]["reward"], 0.357)
            self.assertEqual(snapshot["errors"][0]["category"], "browser")

    def test_native_summary_and_verifier_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            write_json(
                run_dir / "summary.json",
                {
                    "model": "model",
                    "max_steps": 400,
                    "run": {"started_at": "a", "ended_at": "b"},
                    "overall": {"total": 1, "runs": 1, "avg_mean_score": 0.5},
                },
            )
            write_json(
                run_dir / "agriculture_003_r0.json",
                {"status": "completed", "trajectory": [{"step": 1}]},
            )
            write_json(
                run_dir / "agriculture_003_r0_verify.json",
                {"status": "FAIL", "score": 0.5, "checks": []},
            )

            snapshot = inspect_run(run_dir, "auto")

            self.assertEqual(snapshot["mode"], "native")
            self.assertTrue(snapshot["terminal"])
            self.assertEqual(snapshot["mean_reward"], 0.5)
            self.assertEqual(snapshot["trials"][0]["step"], 1)

    def test_step_fingerprint_uses_buckets(self) -> None:
        snapshot = {
            "terminal": False,
            "counts": {"running": 1},
            "mean_reward": None,
            "errors": [],
            "trials": [
                {
                    "name": "trial",
                    "status": "running",
                    "agent_status": "running",
                    "verifier_status": "unknown",
                    "step": 10,
                    "reward": None,
                }
            ],
        }
        first = status_fingerprint(snapshot, step_delta=10)
        snapshot["trials"][0]["step"] = 19
        self.assertEqual(first, status_fingerprint(snapshot, step_delta=10))
        snapshot["trials"][0]["step"] = 20
        self.assertNotEqual(first, status_fingerprint(snapshot, step_delta=10))

    def test_run_card_has_no_destructive_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            write_json(
                run_dir / "result.json",
                {"finished_at": None, "n_total_trials": 1, "stats": {}},
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "run_card.py"),
                    "--mode",
                    "harbor",
                    "--run-dir",
                    str(run_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            lowered = result.stdout.lower()
            self.assertIn("monitor.py", result.stdout)
            self.assertNotIn(" kill ", lowered)
            self.assertNotIn(" rm ", lowered)
            self.assertNotIn("token=", lowered)


if __name__ == "__main__":
    unittest.main()
