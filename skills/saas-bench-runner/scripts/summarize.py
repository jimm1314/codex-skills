#!/usr/bin/env python3
"""Print a concise, read-only summary of a Harbor/native SaaS-Bench run."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from _runlib import format_status, inspect_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("auto", "harbor", "native"), default="auto")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = inspect_run(args.run_dir, args.mode)
    categories = Counter(item["category"] for item in snapshot.get("errors") or [])
    if args.json:
        payload = dict(snapshot)
        payload["error_categories"] = dict(sorted(categories.items()))
        payload["strict_parity"] = "NOT_PROVEN_WITHOUT_MATCHED_PROVENANCE"
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(format_status(snapshot))
    print("\n结果解释:")
    print(
        f"- 错误类别: {dict(sorted(categories.items())) if categories else '未检测到已知错误'}"
    )
    print("- 严格对照资格: 尚未证明；需使用 compare.py 核对匹配参数和来源证据。")
    print("- 原始结果未被修改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
