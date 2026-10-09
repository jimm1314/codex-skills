#!/usr/bin/env python3
"""Compare existing native and Harbor SaaS-Bench results without rerunning."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from _runlib import read_json, redact


NATIVE_RE = re.compile(r"^(?P<task>.+)_r(?P<run>\d+)\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-run", type=Path, required=True)
    parser.add_argument("--harbor-run", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def signature(verifier: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    result: list[tuple[str, int]] = []
    for check in verifier.get("checks") or []:
        if isinstance(check, dict):
            result.append(
                (str(check.get("label") or ""), int(check.get("weight") or 0))
            )
    return tuple(result)


def native_records(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = read_json(run_dir / "summary.json") or {}
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*_r*.json")):
        if path.name.endswith("_verify.json"):
            continue
        match = NATIVE_RE.match(path.name)
        if not match:
            continue
        agent = read_json(path) or {}
        verify = read_json(run_dir / f"{path.stem}_verify.json") or {}
        records.append(
            {
                "task": match.group("task"),
                "run": f"r{match.group('run')}",
                "agent_status": str(agent.get("status") or "unknown"),
                "verifier_status": str(verify.get("status") or "unknown"),
                "score": verify.get("score"),
                "signature": signature(verify),
            }
        )
    metadata = {
        "model": summary.get("model"),
        "max_steps": summary.get("max_steps"),
        "judge_mode": "not-recorded",
        "terminal": bool((summary.get("run") or {}).get("ended_at"))
        if isinstance(summary.get("run"), dict)
        else False,
    }
    return metadata, records


def harbor_records(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = read_json(run_dir / "result.json") or {}
    records: list[dict[str, Any]] = []
    models: set[str] = set()
    steps: set[int] = set()
    judge_modes: set[str] = set()
    checksums: dict[str, set[str]] = defaultdict(set)
    for trial_dir in sorted(path for path in run_dir.iterdir() if path.is_dir()):
        result = read_json(trial_dir / "result.json") or {}
        config = read_json(trial_dir / "config.json") or {}
        if not result and not config:
            continue
        effective = (
            result.get("config") if isinstance(result.get("config"), dict) else config
        )
        task_name = str(result.get("task_name") or "")
        task = task_name.rsplit("/", 1)[-1] if task_name else ""
        if not task:
            task_path = (
                (effective.get("task") or {}).get("path", "")
                if isinstance(effective.get("task"), dict)
                else ""
            )
            task = (
                Path(str(task_path)).name
                if task_path
                else trial_dir.name.split("__", 1)[0]
            )
        agent_cfg = (
            effective.get("agent") if isinstance(effective.get("agent"), dict) else {}
        )
        if agent_cfg.get("model_name"):
            models.add(str(agent_cfg["model_name"]))
        kwargs = (
            agent_cfg.get("kwargs") if isinstance(agent_cfg.get("kwargs"), dict) else {}
        )
        if isinstance(kwargs.get("max_steps"), int):
            steps.add(int(kwargs["max_steps"]))
        verifier_cfg = (
            effective.get("verifier")
            if isinstance(effective.get("verifier"), dict)
            else {}
        )
        verifier_kwargs = (
            verifier_cfg.get("kwargs")
            if isinstance(verifier_cfg.get("kwargs"), dict)
            else {}
        )
        judge_modes.add(
            "judge-remap"
            if verifier_kwargs.get("judge_model_override")
            else "upstream-exact"
        )
        if result.get("task_checksum"):
            checksums[task].add(str(result["task_checksum"]))

        agent_meta = (
            result.get("agent_result", {}).get("metadata", {}).get("saas_bench", {})
            if isinstance(result.get("agent_result"), dict)
            else {}
        )
        agent_file = read_json(trial_dir / "agent" / "saas_bench_result.json") or {}
        verify = read_json(trial_dir / "verifier" / "saas_bench_verify.json") or {}
        verifier_result = result.get("verifier_result")
        score = None
        if isinstance(verifier_result, dict) and isinstance(
            verifier_result.get("rewards"), dict
        ):
            score = verifier_result["rewards"].get("reward")
        if score is None:
            score = verify.get("score")
        records.append(
            {
                "task": task,
                "run": trial_dir.name,
                "agent_status": str(
                    agent_meta.get("status") or agent_file.get("status") or "unknown"
                ),
                "verifier_status": str(
                    verify.get("status")
                    or ("ERROR" if result.get("exception_info") else "unknown")
                ),
                "score": score,
                "signature": signature(verify),
            }
        )
    metadata = {
        "model": sorted(models),
        "max_steps": sorted(steps),
        "judge_mode": sorted(judge_modes),
        "task_checksums": {
            key: sorted(value) for key, value in sorted(checksums.items())
        },
        "terminal": bool(root.get("finished_at")),
    }
    return metadata, records


def numeric_scores(records: list[dict[str, Any]]) -> list[float]:
    return [
        float(record["score"])
        for record in records
        if isinstance(record.get("score"), (int, float))
    ]


def main() -> int:
    args = parse_args()
    native_dir = args.native_run.expanduser().resolve()
    harbor_dir = args.harbor_run.expanduser().resolve()
    if not native_dir.is_dir() or not harbor_dir.is_dir():
        raise SystemExit(
            "Both --native-run and --harbor-run must be existing directories"
        )

    native_meta, native = native_records(native_dir)
    harbor_meta, harbor = harbor_records(harbor_dir)
    native_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    harbor_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in native:
        native_by_task[record["task"]].append(record)
    for record in harbor:
        harbor_by_task[record["task"]].append(record)

    native_tasks = set(native_by_task)
    harbor_tasks = set(harbor_by_task)
    blockers: list[str] = []
    warnings: list[str] = []
    if native_tasks != harbor_tasks:
        blockers.append(
            f"Task 集不一致: native-only={sorted(native_tasks - harbor_tasks)}, "
            f"harbor-only={sorted(harbor_tasks - native_tasks)}"
        )
    harbor_models = set(harbor_meta["model"])
    if (
        native_meta.get("model")
        and harbor_models
        and native_meta["model"] not in harbor_models
    ):
        blockers.append(
            f"模型不一致: native={native_meta['model']}, harbor={sorted(harbor_models)}"
        )
    harbor_steps = set(harbor_meta["max_steps"])
    if (
        native_meta.get("max_steps")
        and harbor_steps
        and native_meta["max_steps"] not in harbor_steps
    ):
        blockers.append(
            f"max_steps 不一致: native={native_meta['max_steps']}, harbor={sorted(harbor_steps)}"
        )
    if not native_meta["terminal"] or not harbor_meta["terminal"]:
        blockers.append("至少一侧没有终态结果。")

    task_rows: list[dict[str, Any]] = []
    for task in sorted(native_tasks | harbor_tasks):
        left = native_by_task.get(task, [])
        right = harbor_by_task.get(task, [])
        left_signatures = {
            record["signature"] for record in left if record["signature"]
        }
        right_signatures = {
            record["signature"] for record in right if record["signature"]
        }
        signature_match = bool(
            left_signatures and right_signatures and left_signatures == right_signatures
        )
        if left and right and not signature_match:
            blockers.append(f"{task} verifier labels/weights 未证明一致。")
        if len(left) != len(right):
            warnings.append(
                f"{task} 重复次数不同: native={len(left)}, harbor={len(right)}"
            )
        left_scores = numeric_scores(left)
        right_scores = numeric_scores(right)
        task_rows.append(
            {
                "task": task,
                "native_runs": len(left),
                "harbor_runs": len(right),
                "native_mean": statistics.fmean(left_scores) if left_scores else None,
                "harbor_mean": statistics.fmean(right_scores) if right_scores else None,
                "signature_match": signature_match,
                "native_agent_status": dict(Counter(r["agent_status"] for r in left)),
                "harbor_agent_status": dict(Counter(r["agent_status"] for r in right)),
                "native_verifier_status": dict(
                    Counter(r["verifier_status"] for r in left)
                ),
                "harbor_verifier_status": dict(
                    Counter(r["verifier_status"] for r in right)
                ),
            }
        )

    warnings.append(
        "原生历史结果未记录运行时 Task/verifier 哈希和 Judge 映射；严格来源一致性无法由结果目录证明。"
    )
    if "judge-remap" in harbor_meta["judge_mode"]:
        warnings.append(
            "Harbor 使用 judge-remap，而 native Judge 模式未记录；Judge 题不可声明严格可比。"
        )

    payload = {
        "native_run": str(native_dir),
        "harbor_run": str(harbor_dir),
        "execution_contract": "MATCHED" if not blockers else "MISMATCH",
        "strict_provenance": "NOT_PROVEN",
        "native_metadata": native_meta,
        "harbor_metadata": harbor_meta,
        "tasks": task_rows,
        "blockers": [redact(item) for item in blockers],
        "warnings": [redact(item) for item in warnings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"执行契约: {payload['execution_contract']}")
        print("严格来源一致性: NOT_PROVEN")
        for row in task_rows:
            print(
                f"- {row['task']}: native={row['native_runs']}次/{row['native_mean']} "
                f"harbor={row['harbor_runs']}次/{row['harbor_mean']} "
                f"checks={'一致' if row['signature_match'] else '未证明一致'}"
            )
            print(
                f"  agent native={row['native_agent_status']} harbor={row['harbor_agent_status']}; "
                f"verifier native={row['native_verifier_status']} harbor={row['harbor_verifier_status']}"
            )
        print("阻塞:")
        for item in blockers or ["无执行契约阻塞"]:
            print(f"- {redact(item)}")
        print("警告:")
        for item in warnings or ["无"]:
            print(f"- {redact(item)}")
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
