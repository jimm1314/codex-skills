#!/usr/bin/env python3
"""Read-only parsers shared by the SaaS-Bench runner helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


_STEP_RE = re.compile(r"step_(\d+)_request\.json$")
_NATIVE_AGENT_RE = re.compile(r"^(?P<task>.+)_r(?P<run>\d+)\.json$")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[-_ ]?key|authorization|cookie|password|session_router_token|token)"
    r"(\s*[:=]\s*)([^\s,;}\]]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")


def redact(text: Any, *, limit: int = 600) -> str:
    """Bound and redact likely credential assignments in human-facing output."""

    value = str(text or "").replace("\x00", "")
    value = _BEARER_RE.sub("Bearer <redacted>", value)
    value = _SECRET_ASSIGNMENT_RE.sub(r"\1\2<redacted>", value)
    value = " ".join(value.split())
    if len(value) > limit:
        return value[: limit - 1] + "…"
    return value


def read_json(
    path: Path, errors: Optional[list[dict[str, str]]] = None
) -> Optional[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        if errors is not None:
            errors.append(
                {
                    "category": "artifact",
                    "source": str(path),
                    "message": redact(f"Cannot parse JSON: {exc}"),
                }
            )
        return None
    return value if isinstance(value, dict) else None


def classify_error(text: Any) -> str:
    normalized = str(text or "").lower()
    if any(
        token in normalized
        for token in ("llm_judge", "llm judge", "judge model", "judge api")
    ):
        return "judge"
    if any(
        token in normalized
        for token in ("browser_dead", "playwright", "chrome", "/state", "/act")
    ):
        return "browser"
    if any(
        token in normalized
        for token in (
            "session router",
            "session_router",
            "create_vm_session",
            "sandbox",
            "vm start",
            "vm creation",
        )
    ):
        return "session_router"
    if any(
        token in normalized
        for token in ("sql error", "docker", "container", "preflight", "env-server")
    ):
        return "verifier_or_app_infra"
    if any(
        token in normalized
        for token in (
            "modelprovidererror",
            "invalid frequency_penalty",
            "llm call failed",
            "model is currently offline",
        )
    ):
        return "model_api"
    if any(
        token in normalized for token in ("timeout", "timed out", "connection refused")
    ):
        return "transport"
    return "other"


def _latest_step(trace_dir: Path) -> int:
    latest = 0
    if not trace_dir.is_dir():
        return latest
    for path in trace_dir.glob("step_*_request.json"):
        match = _STEP_RE.search(path.name)
        if match:
            latest = max(latest, int(match.group(1)))
    return latest


def _latest_mtime(paths: list[Path]) -> Optional[str]:
    mtimes: list[float] = []
    for path in paths:
        try:
            mtimes.append(path.stat().st_mtime)
        except OSError:
            continue
    if not mtimes:
        return None
    return datetime.fromtimestamp(max(mtimes), tz=timezone.utc).isoformat()


def detect_mode(run_dir: Path) -> str:
    run_dir = run_dir.expanduser().resolve()
    root_result = read_json(run_dir / "result.json")
    if root_result and (
        "n_total_trials" in root_result or isinstance(root_result.get("stats"), dict)
    ):
        return "harbor"
    if (run_dir / "summary.json").is_file() or (run_dir / "traces").is_dir():
        return "native"
    if any(run_dir.glob("*_r*_verify.json")) or any(run_dir.glob("*_r*.json")):
        return "native"
    if (run_dir / "job.log").exists() or (run_dir / "lock.json").exists():
        return "harbor"
    raise ValueError(f"Cannot detect run mode from {run_dir}")


def inspect_harbor(run_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    root = read_json(run_dir / "result.json", errors) or {}
    stats = root.get("stats") if isinstance(root.get("stats"), dict) else {}
    trials: list[dict[str, Any]] = []
    judge_modes: set[str] = set()
    models: set[str] = set()
    max_steps: set[int] = set()

    for trial_dir in sorted(path for path in run_dir.iterdir() if path.is_dir()):
        config = read_json(trial_dir / "config.json", errors) or {}
        result = read_json(trial_dir / "result.json", errors) or {}
        if not config and not result and not (trial_dir / "trial.log").exists():
            continue

        result_config = (
            result.get("config") if isinstance(result.get("config"), dict) else {}
        )
        effective_config = result_config or config
        task_name = str(result.get("task_name") or "")
        task = task_name.rsplit("/", 1)[-1] if task_name else ""
        if not task:
            task_path = (
                effective_config.get("task", {}).get("path", "")
                if isinstance(effective_config.get("task"), dict)
                else ""
            )
            task = (
                Path(str(task_path)).name
                if task_path
                else trial_dir.name.split("__", 1)[0]
            )

        agent_cfg = (
            effective_config.get("agent")
            if isinstance(effective_config.get("agent"), dict)
            else {}
        )
        model = str(agent_cfg.get("model_name") or "unknown")
        models.add(model)
        kwargs = (
            agent_cfg.get("kwargs") if isinstance(agent_cfg.get("kwargs"), dict) else {}
        )
        if isinstance(kwargs.get("max_steps"), int):
            max_steps.add(int(kwargs["max_steps"]))

        verifier_cfg = (
            effective_config.get("verifier")
            if isinstance(effective_config.get("verifier"), dict)
            else {}
        )
        verifier_kwargs = (
            verifier_cfg.get("kwargs")
            if isinstance(verifier_cfg.get("kwargs"), dict)
            else {}
        )
        remap = verifier_kwargs.get("judge_model_override")
        judge_modes.add("judge-remap" if remap else "upstream-exact")

        agent_file = (
            read_json(trial_dir / "agent" / "saas_bench_result.json", errors) or {}
        )
        metadata = (
            result.get("agent_result", {}).get("metadata", {}).get("saas_bench", {})
            if isinstance(result.get("agent_result"), dict)
            else {}
        )
        agent_status = str(
            metadata.get("status") or agent_file.get("status") or "unknown"
        )
        trace_dir = trial_dir / "agent" / "traces"
        step = max(int(metadata.get("steps") or 0), _latest_step(trace_dir))

        verifier_file = (
            read_json(trial_dir / "verifier" / "saas_bench_verify.json", errors) or {}
        )
        verifier_status = str(verifier_file.get("status") or "unknown")
        reward = None
        verifier_result = result.get("verifier_result")
        if isinstance(verifier_result, dict):
            rewards = verifier_result.get("rewards")
            if isinstance(rewards, dict):
                reward = rewards.get("reward")
        if reward is None and "score" in verifier_file:
            reward = verifier_file.get("score")

        exception = result.get("exception_info")
        finished = bool(result.get("finished_at"))
        if finished and exception:
            status = "error"
        elif finished:
            status = "completed"
        else:
            status = "running"

        if isinstance(exception, dict):
            message = exception.get("exception_message") or exception.get(
                "exception_type"
            )
            errors.append(
                {
                    "category": classify_error(message),
                    "source": trial_dir.name,
                    "message": redact(message),
                }
            )
        if agent_status not in ("unknown", "completed"):
            details = agent_file.get("error_steps") or []
            message = (
                details[0] if isinstance(details, list) and details else agent_status
            )
            errors.append(
                {
                    "category": classify_error(message),
                    "source": f"{trial_dir.name}/agent",
                    "message": redact(message),
                }
            )
        judge_errors = verifier_file.get("judge_infrastructure_errors") or []
        if isinstance(judge_errors, list):
            for message in judge_errors[:3]:
                errors.append(
                    {
                        "category": "judge",
                        "source": f"{trial_dir.name}/verifier",
                        "message": redact(message),
                    }
                )
        checks = verifier_file.get("checks") or []
        if isinstance(checks, list):
            for check in checks:
                if not isinstance(check, dict):
                    continue
                detail = str(check.get("detail") or "")
                normalized = detail.lower()
                if "sql error" in normalized or normalized.startswith("exception:"):
                    errors.append(
                        {
                            "category": classify_error(detail),
                            "source": f"{trial_dir.name}/verifier",
                            "message": redact(
                                f"{check.get('label', 'check')}: {detail}"
                            ),
                        }
                    )

        observed_files = [
            trial_dir / "result.json",
            trial_dir / "trial.log",
            trial_dir / "agent" / "saas_bench_result.json",
            trial_dir / "verifier" / "saas_bench_verify.json",
            *trace_dir.glob("step_*_request.json"),
        ]
        trials.append(
            {
                "name": trial_dir.name,
                "task": task,
                "status": status,
                "agent_status": agent_status,
                "verifier_status": verifier_status,
                "step": step,
                "reward": reward,
                "updated_at": _latest_mtime(observed_files),
            }
        )

    evals = stats.get("evals") if isinstance(stats.get("evals"), dict) else {}
    means: list[float] = []
    for evaluation in evals.values():
        if not isinstance(evaluation, dict):
            continue
        for metric in evaluation.get("metrics") or []:
            if isinstance(metric, dict) and isinstance(
                metric.get("mean"), (int, float)
            ):
                means.append(float(metric["mean"]))

    counts = {
        "total": int(root.get("n_total_trials") or len(trials)),
        "completed": int(stats.get("n_completed_trials") or 0),
        "errored": int(stats.get("n_errored_trials") or 0),
        "running": int(stats.get("n_running_trials") or 0),
        "pending": int(stats.get("n_pending_trials") or 0),
        "cancelled": int(stats.get("n_cancelled_trials") or 0),
    }
    if not stats and trials:
        counts["completed"] = sum(t["status"] == "completed" for t in trials)
        counts["errored"] = sum(t["status"] == "error" for t in trials)
        counts["running"] = sum(t["status"] == "running" for t in trials)

    return {
        "mode": "harbor",
        "run_dir": str(run_dir),
        "terminal": bool(root.get("finished_at")),
        "started_at": root.get("started_at"),
        "updated_at": root.get("updated_at") or _latest_mtime([run_dir / "job.log"]),
        "finished_at": root.get("finished_at"),
        "counts": counts,
        "mean_reward": means[0] if len(means) == 1 else means or None,
        "models": sorted(models),
        "max_steps": sorted(max_steps),
        "judge_modes": sorted(judge_modes),
        "trials": trials,
        "errors": dedupe_errors(errors),
    }


def inspect_native(run_dir: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    summary = read_json(run_dir / "summary.json", errors) or {}
    traces_root = run_dir / "traces"
    keys: set[tuple[str, int]] = set()

    for path in run_dir.glob("*_r*.json"):
        if path.name.endswith("_verify.json"):
            continue
        match = _NATIVE_AGENT_RE.match(path.name)
        if match:
            keys.add((match.group("task"), int(match.group("run"))))
    if traces_root.is_dir():
        for path in traces_root.iterdir():
            if not path.is_dir():
                continue
            match = re.match(r"^(?P<task>.+)_r(?P<run>\d+)$", path.name)
            if match:
                keys.add((match.group("task"), int(match.group("run"))))

    trials: list[dict[str, Any]] = []
    for task, run_idx in sorted(keys):
        stem = f"{task}_r{run_idx}"
        agent_path = run_dir / f"{stem}.json"
        verify_path = run_dir / f"{stem}_verify.json"
        agent = read_json(agent_path, errors) or {}
        verifier = read_json(verify_path, errors) or {}
        trace_dir = traces_root / stem
        step = max(len(agent.get("trajectory") or []), _latest_step(trace_dir))
        agent_status = str(
            agent.get("status") or ("running" if trace_dir.exists() else "unknown")
        )
        verifier_status = str(verifier.get("status") or "unknown")
        if verify_path.exists():
            status = "error" if verifier_status in ("ERROR", "SKIP") else "completed"
        elif agent_path.exists():
            status = "verifying"
        else:
            status = "running"

        if agent_status not in ("unknown", "completed", "running"):
            details = agent.get("error_steps") or []
            message = (
                details[0] if isinstance(details, list) and details else agent_status
            )
            errors.append(
                {
                    "category": classify_error(message),
                    "source": f"{stem}/agent",
                    "message": redact(message),
                }
            )
        if verifier_status in ("ERROR", "SKIP"):
            message = verifier.get("error") or verifier_status
            errors.append(
                {
                    "category": classify_error(message),
                    "source": f"{stem}/verifier",
                    "message": redact(message),
                }
            )
        checks = verifier.get("checks") or []
        if isinstance(checks, list):
            for check in checks:
                if not isinstance(check, dict):
                    continue
                detail = str(check.get("detail") or "")
                normalized = detail.lower()
                if (
                    "llm_judge" in normalized
                    or "sql error" in normalized
                    or normalized.startswith("exception:")
                ):
                    errors.append(
                        {
                            "category": classify_error(detail),
                            "source": f"{stem}/verifier",
                            "message": redact(
                                f"{check.get('label', 'check')}: {detail}"
                            ),
                        }
                    )

        trials.append(
            {
                "name": stem,
                "task": task,
                "status": status,
                "agent_status": agent_status,
                "verifier_status": verifier_status,
                "step": step,
                "reward": verifier.get("score"),
                "updated_at": _latest_mtime(
                    [agent_path, verify_path, *trace_dir.glob("step_*_request.json")]
                ),
            }
        )

    errors_log = run_dir / "errors.log"
    if errors_log.is_file():
        try:
            lines = errors_log.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError as exc:
            lines = [f"Cannot read errors.log: {exc}"]
        for line in lines[-10:]:
            if line.strip():
                errors.append(
                    {
                        "category": classify_error(line),
                        "source": "errors.log",
                        "message": redact(line),
                    }
                )

    overall = summary.get("overall") if isinstance(summary.get("overall"), dict) else {}
    total_tasks = int(overall.get("total") or 0)
    runs = int(overall.get("runs") or 0)
    total = total_tasks * runs if total_tasks and runs else len(trials)
    terminal = (
        bool((summary.get("run") or {}).get("ended_at"))
        if isinstance(summary.get("run"), dict)
        else False
    )
    completed = sum(t["status"] == "completed" for t in trials)
    errored = sum(t["status"] == "error" for t in trials)
    running = (
        0 if terminal else sum(t["status"] in ("running", "verifying") for t in trials)
    )

    return {
        "mode": "native",
        "run_dir": str(run_dir),
        "terminal": terminal,
        "started_at": (summary.get("run") or {}).get("started_at")
        if isinstance(summary.get("run"), dict)
        else None,
        "updated_at": _latest_mtime(
            [
                run_dir / "summary.json",
                run_dir / "errors.log",
                *run_dir.glob("*_r*.json"),
            ]
        ),
        "finished_at": (summary.get("run") or {}).get("ended_at")
        if isinstance(summary.get("run"), dict)
        else None,
        "counts": {
            "total": total,
            "completed": completed,
            "errored": errored,
            "running": running,
            "pending": max(0, total - completed - errored - running),
            "cancelled": 0,
        },
        "mean_reward": overall.get("avg_mean_score"),
        "models": [str(summary.get("model"))] if summary.get("model") else [],
        "max_steps": [int(summary["max_steps"])]
        if isinstance(summary.get("max_steps"), int)
        else [],
        "judge_modes": ["not-recorded"],
        "trials": trials,
        "errors": dedupe_errors(errors),
    }


def dedupe_errors(errors: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for item in errors:
        key = (
            item.get("category", ""),
            item.get("source", ""),
            item.get("message", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def inspect_run(run_dir: Path, mode: str = "auto") -> dict[str, Any]:
    resolved = run_dir.expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(f"Run directory not found: {resolved}")
    selected = detect_mode(resolved) if mode == "auto" else mode
    if selected == "harbor":
        return inspect_harbor(resolved)
    if selected == "native":
        return inspect_native(resolved)
    raise ValueError(f"Unsupported mode: {selected}")


def status_fingerprint(snapshot: dict[str, Any], *, step_delta: int = 10) -> str:
    compact = {
        "terminal": snapshot.get("terminal"),
        "counts": snapshot.get("counts"),
        "mean_reward": snapshot.get("mean_reward"),
        "errors": snapshot.get("errors"),
        "trials": [
            {
                "name": trial.get("name"),
                "status": trial.get("status"),
                "agent_status": trial.get("agent_status"),
                "verifier_status": trial.get("verifier_status"),
                "step_bucket": int(trial.get("step") or 0) // max(1, step_delta),
                "reward": trial.get("reward"),
            }
            for trial in snapshot.get("trials") or []
        ],
    }
    return json.dumps(compact, ensure_ascii=False, sort_keys=True)


def format_status(snapshot: dict[str, Any], *, errors_only: bool = False) -> str:
    lines: list[str] = []
    errors = snapshot.get("errors") or []
    if errors_only:
        if not errors:
            return "未发现已分类的运行错误。"
        lines.append(f"错误摘要（{len(errors)}）:")
        for item in errors[:12]:
            lines.append(
                f"- [{item.get('category')}] {item.get('source')}: {item.get('message')}"
            )
        if len(errors) > 12:
            lines.append(f"- 其余 {len(errors) - 12} 条未展开。")
        return "\n".join(lines)

    counts = snapshot.get("counts") or {}
    state = "已结束" if snapshot.get("terminal") else "运行中/未形成终态"
    lines.extend(
        [
            f"模式: {snapshot.get('mode')}",
            f"目录: {snapshot.get('run_dir')}",
            f"状态: {state}",
            (
                "进度: total={total} completed={completed} errored={errored} "
                "running={running} pending={pending} cancelled={cancelled}"
            ).format(
                **{
                    key: counts.get(key, 0)
                    for key in (
                        "total",
                        "completed",
                        "errored",
                        "running",
                        "pending",
                        "cancelled",
                    )
                }
            ),
            f"模型: {', '.join(snapshot.get('models') or []) or '未记录'}",
            f"最大步数: {', '.join(map(str, snapshot.get('max_steps') or [])) or '未记录'}",
            f"Judge 模式: {', '.join(snapshot.get('judge_modes') or []) or '未记录'}",
            f"平均分: {snapshot.get('mean_reward') if snapshot.get('mean_reward') is not None else '尚无'}",
            f"最近更新: {snapshot.get('updated_at') or '未知'}",
        ]
    )
    trials = snapshot.get("trials") or []
    if trials:
        lines.append("Trials:")
        for trial in trials[:24]:
            reward = trial.get("reward")
            lines.append(
                "- {name}: task={task} status={status} agent={agent} verifier={verifier} "
                "step={step} reward={reward}".format(
                    name=trial.get("name"),
                    task=trial.get("task"),
                    status=trial.get("status"),
                    agent=trial.get("agent_status"),
                    verifier=trial.get("verifier_status"),
                    step=trial.get("step", 0),
                    reward=reward if reward is not None else "-",
                )
            )
        if len(trials) > 24:
            lines.append(f"- 其余 {len(trials) - 24} 个 Trial 未展开。")
    if errors:
        lines.append(f"错误分类: {len(errors)} 条（使用 --errors 查看有界摘要）")
    return "\n".join(lines)
