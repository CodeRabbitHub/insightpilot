"""PostToolUse hook: after any git commit, append the commit's hash and
stat to plans/logs/_auto-capture.md so /capture can pre-fill the slice log
mechanically. Never blocks anything.
"""
import datetime
import json
import pathlib
import subprocess
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    if "git commit" not in command:
        return 0
    try:
        info = subprocess.run(
            ["git", "log", "-1", "--stat"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception:
        return 0
    if not info.strip():
        return 0
    log_dir = pathlib.Path("plans/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with (log_dir / "_auto-capture.md").open("a", encoding="utf-8") as fh:
        fh.write(f"\n## Commit at {stamp}\n```\n{info}```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
