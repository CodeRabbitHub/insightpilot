"""PreToolUse hook: blocks destructive shell commands before they run.

Exit 2 = block the tool call and show stderr to the agent as feedback.
"""
import json
import re
import sys

PATTERNS = [
    (r"rm\s+(-\w*r\w*f|-\w*f\w*r)\b", "recursive force delete"),
    (r"Remove-Item\b(?=.*-Recurse)(?=.*-Force)", "recursive force delete"),
    (r"git\s+push\s+(?!.*--force-with-lease).*(--force|-f)\b", "force push"),
    (r"git\s+reset\s+--hard", "hard reset discards uncommitted work"),
    (r"git\s+clean\s+-\w*f", "git clean deletes untracked files"),
    (r"(>|>>)\s*\.env\b", "writing to .env"),
    (r"git\s+commit\b.*--no-verify", "bypassing hooks on commit"),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    for pattern, why in PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"Blocked by danger_block hook: {why}. "
                "If this is genuinely needed, ask the user to run or "
                "explicitly approve it.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
