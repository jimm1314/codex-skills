#!/usr/bin/env python3
"""Inspect or low-noise poll a Harbor/native SaaS-Bench run directory."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from _runlib import format_status, inspect_run, status_fingerprint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("auto", "harbor", "native"), default="auto")
    parser.add_argument("--run-dir", type=Path, required=True)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument(
        "--once", action="store_true", help="Inspect once (default)."
    )
    operation.add_argument(
        "--follow", action="store_true", help="Poll until a terminal artifact appears."
    )
    parser.add_argument(
        "--errors", action="store_true", help="Print only bounded error summaries."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit the full bounded snapshot as JSON."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (minimum 5).",
    )
    parser.add_argument(
        "--heartbeat",
        type=int,
        default=600,
        help="Print unchanged state after this many seconds.",
    )
    parser.add_argument(
        "--step-delta",
        type=int,
        default=10,
        help="Treat each N new steps as a state change.",
    )
    return parser.parse_args()


def render(snapshot: dict, args: argparse.Namespace) -> str:
    if args.json:
        return json.dumps(snapshot, ensure_ascii=False, indent=2)
    return format_status(snapshot, errors_only=args.errors)


def main() -> int:
    args = parse_args()
    if args.interval < 5:
        raise SystemExit("--interval must be at least 5 seconds")
    if args.heartbeat < args.interval:
        raise SystemExit("--heartbeat must be greater than or equal to --interval")
    if args.step_delta < 1:
        raise SystemExit("--step-delta must be at least 1")

    if not args.follow:
        print(render(inspect_run(args.run_dir, args.mode), args))
        return 0

    previous: Optional[str] = None
    last_print = 0.0
    try:
        while True:
            snapshot = inspect_run(args.run_dir, args.mode)
            fingerprint = status_fingerprint(snapshot, step_delta=args.step_delta)
            now = time.monotonic()
            if fingerprint != previous or now - last_print >= args.heartbeat:
                if last_print:
                    print("", flush=True)
                print(render(snapshot, args), flush=True)
                previous = fingerprint
                last_print = now
            if snapshot.get("terminal"):
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n监控已停止；评测进程未被修改或终止。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
