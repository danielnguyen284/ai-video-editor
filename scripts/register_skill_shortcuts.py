"""Register the local video library in the Codex (.agents/skills) and Claude Code (.claude/skills) discovery directories."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.common import EditorError
from core.skill_shortcuts import check_shortcuts, register_shortcuts


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            rows = check_shortcuts()
            for row in rows:
                print(f"{row['status']:10} {row['invoke']}")
            return int(any(row["status"] != "registered" for row in rows))
        result = register_shortcuts()
        print(f"Registered {result['registered']} repo skills ({result['created']} new files) in {' and '.join(result['folders'])}.")
        return 0
    except (EditorError, OSError, KeyError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
