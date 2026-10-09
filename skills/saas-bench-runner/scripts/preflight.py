#!/usr/bin/env python3
"""Read-only safety preflight for native/Harbor SaaS-Bench evaluations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Optional


TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("harbor", "native", "parity"), required=True)
    parser.add_argument("--harbor-repo", type=Path, required=True)
    parser.add_argument("--saas-bench-repo", type=Path, required=True)
    parser.add_argument(
        "--tasks-root",
        default="tasks/multi-m",
        help="Repo-relative SaaS-Bench task collection containing --category.",
    )
    parser.add_argument("--category", default="Agriculture")
    parser.add_argument("--task", action="append", dest="tasks")
    parser.add_argument(
        "--judge-mode",
        choices=("upstream-exact", "judge-remap"),
        default="upstream-exact",
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--allow-active",
        action="store_true",
        help="Report active Harbor jobs as warnings instead of blockers.",
    )
    parser.add_argument(
        "--active-window-minutes",
        type=int,
        default=120,
        help="Unfinished jobs updated within this window count as active.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip() or result.stderr.strip()
    return result.returncode, output


def declared_env_keys(path: Optional[Path], warnings: list[str]) -> set[str]:
    if path is None:
        return set()
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        warnings.append(f"env-file 不存在: {resolved}")
        return set()
    keys: set[str] = set()
    try:
        lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        warnings.append(f"无法读取 env-file 的变量名: {exc}")
        return set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            keys.add(key)
    return keys


def harbor_job_states(
    harbor_repo: Path, active_window_minutes: int
) -> tuple[list[str], list[str]]:
    active: list[str] = []
    stale: list[str] = []
    root = harbor_repo / "jobs" / "saas-bench"
    if not root.is_dir():
        return active, stale
    cutoff = time.time() - max(1, active_window_minutes) * 60
    for result_path in sorted(root.glob("*/result.json")):
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        stats = result.get("stats") if isinstance(result, dict) else {}
        running = int((stats or {}).get("n_running_trials") or 0)
        pending = int((stats or {}).get("n_pending_trials") or 0)
        if not result.get("finished_at") and (running or pending):
            observed = [result_path, result_path.parent / "job.log"]
            observed.extend(result_path.parent.glob("*/trial.log"))
            mtimes = []
            for path in observed:
                try:
                    mtimes.append(path.stat().st_mtime)
                except OSError:
                    continue
            target = active if mtimes and max(mtimes) >= cutoff else stale
            target.append(str(result_path.parent.resolve()))
    return active, stale


def main() -> int:
    args = parse_args()
    harbor = args.harbor_repo.expanduser().resolve()
    saas = args.saas_bench_repo.expanduser().resolve()
    blockers: list[str] = []
    warnings: list[str] = []
    facts: list[str] = []
    task_records: list[dict[str, Any]] = []

    if not (harbor / "pyproject.toml").is_file():
        blockers.append(f"Harbor 仓库无效: {harbor}")
    if not (saas / "pyproject.toml").is_file() or not (saas / "saas_bench").is_dir():
        blockers.append(f"SaaS-Bench 仓库无效: {saas}")

    tasks_root_rel = Path(args.tasks_root)
    tasks_root = (saas / "tasks").resolve()
    if (
        tasks_root_rel.is_absolute()
        or ".." in tasks_root_rel.parts
        or tasks_root_rel.parts[:1] != ("tasks",)
    ):
        blockers.append(
            f"tasks-root 必须是仓库内 tasks/ 下的相对路径: {args.tasks_root!r}"
        )
        category_dir = (saas / tasks_root_rel / args.category).resolve()
    else:
        category_dir = (saas / tasks_root_rel / args.category).resolve()
    if not category_dir.is_dir() or not category_dir.is_relative_to(tasks_root):
        blockers.append(f"Task category 不存在或越界: {category_dir}")
        discovered: list[str] = []
    else:
        discovered = sorted(
            path.name
            for path in category_dir.iterdir()
            if path.is_dir()
            and (path / "description.md").is_file()
            and (path / "verify.py").is_file()
        )

    requested = args.tasks or discovered
    if not requested:
        blockers.append("没有发现或指定任何 Task。")

    safe_tasks: list[str] = []
    for task_id in requested:
        if not TASK_ID_RE.fullmatch(task_id):
            blockers.append(f"Task ID 非法或可能路径越界: {task_id!r}")
            continue
        source = (category_dir / task_id).resolve()
        if not source.is_relative_to(category_dir) or not source.is_dir():
            blockers.append(f"Task 不存在或越界: {task_id}")
            continue
        missing = [
            name
            for name in ("description.md", "meta.json", "verify.py")
            if not (source / name).is_file()
        ]
        if missing:
            blockers.append(f"{task_id} 缺少文件: {', '.join(missing)}")
            continue
        safe_tasks.append(task_id)

    code, head = git(saas, "rev-parse", "HEAD")
    if code == 0:
        facts.append(f"SaaS-Bench commit: {head}")
    else:
        blockers.append(f"无法读取 SaaS-Bench Git commit: {head}")
    code, task_status = git(
        saas, "status", "--porcelain", "--untracked-files=all", "--", "tasks"
    )
    if code != 0:
        blockers.append(f"无法检查 upstream tasks Git 状态: {task_status}")
    elif task_status:
        blockers.append("upstream tasks 存在 Git 改动；禁止启动。")
    else:
        facts.append("upstream tasks Git 状态干净")

    judge_required = False
    generated_root = harbor / "datasets" / "saas-bench"
    track_path = Path(*tasks_root_rel.parts[1:])
    for task_id in safe_tasks:
        source = category_dir / task_id
        verify_path = source / "verify.py"
        judge_required = judge_required or "MINDRA_API_KEY" in verify_path.read_text(
            encoding="utf-8", errors="replace"
        )
        record: dict[str, Any] = {
            "task_id": task_id,
            "source_description_sha256": sha256(source / "description.md"),
            "source_verify_sha256": sha256(verify_path),
        }
        if args.mode in ("harbor", "parity"):
            generated = (
                generated_root / track_path / args.category / task_id
            ).resolve()
            if not generated.is_relative_to(generated_root.resolve()):
                blockers.append(f"生成 Task 路径越界: {task_id}")
            else:
                instruction = generated / "instruction.md"
                generated_verify = generated / "tests" / "verify.py"
                if not instruction.is_file() or not generated_verify.is_file():
                    blockers.append(f"Harbor 生成 Task 缺失: {task_id}")
                else:
                    record["generated_instruction_sha256"] = sha256(instruction)
                    record["generated_verify_sha256"] = sha256(generated_verify)
                    if (
                        record["source_description_sha256"]
                        != record["generated_instruction_sha256"]
                    ):
                        blockers.append(
                            f"{task_id} instruction 与上游 description 不一致"
                        )
                    if (
                        record["source_verify_sha256"]
                        != record["generated_verify_sha256"]
                    ):
                        blockers.append(f"{task_id} generated verify.py 与上游不一致")
        task_records.append(record)

    declared = declared_env_keys(args.env_file, warnings)
    present = {key for key, value in os.environ.items() if value} | declared
    requirements = {
        "Session Router": {"SESSION_ROUTER_TOKEN"},
        "LLM endpoint": {"LLM_BASE_URL"},
        "Agent authentication": {"LLM_API_KEY", "LLM_HEADERS", "LLM_HEADERS_BASE64"},
    }
    if judge_required:
        requirements["Judge authentication"] = {"MINDRA_API_KEY", "LLM_API_KEY"}
    for label, alternatives in requirements.items():
        if not present.intersection(alternatives):
            blockers.append(
                f"缺少 {label} 变量名；需要其一: {', '.join(sorted(alternatives))}"
            )
        else:
            facts.append(f"{label} 变量名已声明（值未输出）")

    active, stale = harbor_job_states(harbor, args.active_window_minutes)
    if active and args.mode in ("harbor", "parity"):
        message = "检测到活动 Harbor SaaS-Bench job: " + ", ".join(active)
        if args.allow_active:
            warnings.append(message)
        else:
            blockers.append(message)
    if stale and args.mode in ("harbor", "parity"):
        warnings.append(
            "检测到状态未收口但近期无日志更新的历史 Job（不视为活动进程）: "
            + ", ".join(stale)
        )

    if args.judge_mode == "judge-remap":
        warnings.append("Judge-remap 是实验评估语义；结果不得标记为 upstream-exact。")
    else:
        facts.append(
            "声明 Judge 模式: upstream-exact；启动命令仍需复核配置中无 override。"
        )

    payload = {
        "mode": args.mode,
        "judge_mode": args.judge_mode,
        "harbor_repo": str(harbor),
        "saas_bench_repo": str(saas),
        "tasks": task_records,
        "facts": facts,
        "warnings": warnings,
        "blockers": blockers,
        "ready": not blockers,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"预检模式: {args.mode}")
        print(f"Judge 模式: {args.judge_mode}")
        print(f"Tasks: {', '.join(safe_tasks) or '-'}")
        for label, items in (("已验证", facts), ("警告", warnings), ("阻塞", blockers)):
            print(f"{label}:")
            if not items:
                print("- 无")
            for item in items:
                print(f"- {item}")
        print(f"结论: {'可以进入人工确认阶段' if not blockers else '禁止启动'}")
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
