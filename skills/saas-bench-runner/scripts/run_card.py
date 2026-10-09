#!/usr/bin/env python3
"""Print safe, copyable Bash commands for an existing SaaS-Bench run directory."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path

from _runlib import detect_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("auto", "harbor", "native"), default="auto")
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def command(*parts: object) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"Run directory not found: {run_dir}")
    mode = detect_mode(run_dir) if args.mode == "auto" else args.mode
    scripts = Path(__file__).resolve().parent

    print("运行后操作卡")
    print(f"模式: {mode}")
    print(f"运行目录: {run_dir}")
    print("\n查看一次状态:")
    print(
        command(
            "python3",
            scripts / "monitor.py",
            "--mode",
            mode,
            "--run-dir",
            run_dir,
            "--once",
        )
    )
    print("\n低噪持续监控:")
    print(
        command(
            "python3",
            scripts / "monitor.py",
            "--mode",
            mode,
            "--run-dir",
            run_dir,
            "--follow",
            "--interval",
            30,
            "--heartbeat",
            600,
            "--step-delta",
            10,
        )
    )
    print("\n查看有界错误摘要:")
    print(
        command(
            "python3",
            scripts / "monitor.py",
            "--mode",
            mode,
            "--run-dir",
            run_dir,
            "--errors",
        )
    )

    log_candidates = (
        [run_dir / "job.log"]
        if mode == "harbor"
        else [run_dir / "controller.log", run_dir / "run.log", run_dir / "errors.log"]
    )
    logs = [path for path in log_candidates if path.is_file()]
    if logs:
        print("\n跟随现有日志:")
        for path in logs:
            print(command("tail", "-n", 100, "-f", path))
    else:
        print("\n未检测到可跟随的主日志文件；使用 monitor.py 读取结构化进度。")

    if mode == "harbor":
        print("\n列出 Trial 日志:")
        print(command("find", run_dir, "-name", "trial.log", "-type", "f", "-print"))
    else:
        print("\n列出原生 Trace 目录:")
        print(
            command(
                "find",
                run_dir / "traces",
                "-mindepth",
                1,
                "-maxdepth",
                1,
                "-type",
                "d",
                "-print",
            )
        )

    print("\n生成最终摘要:")
    print(
        command(
            "python3", scripts / "summarize.py", "--mode", mode, "--run-dir", run_dir
        )
    )
    print("\n在新 Codex Session 恢复监控:")
    print(f"$saas-bench-runner 恢复监控这个运行目录：{run_dir}。不要启动新任务。")
    print("\n注意: 操作卡不包含停止进程、删除 VM、删除结果或输出凭证的命令。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
