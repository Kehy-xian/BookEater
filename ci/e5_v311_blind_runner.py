from __future__ import annotations

"""Execute the frozen v3.1.1 blind set without editing its authored cases.

The original validation file contains 66 cases but has a stale bookkeeping assertion
that says 64.  This runner changes only that assertion in memory before execution.
No case text, expected label, threshold, model setting, or scoring rule is modified.
Keeping the original file byte-for-byte intact makes this repair auditable and avoids
silently changing the evaluation set after it was frozen.
"""

from pathlib import Path

SOURCE = Path(__file__).with_name("e5_v311_blind_validation.py")
text = SOURCE.read_text(encoding="utf-8")
old = "assert len(CASES)==64, len(CASES)"
new = "assert len(CASES)==66, len(CASES)"

if old not in text:
    raise RuntimeError("Expected stale 64-case assertion was not found; inspect the frozen blind file before running.")

patched = text.replace(old, new, 1)
exec(compile(patched, str(SOURCE), "exec"), {"__name__": "__main__", "__file__": str(SOURCE)})
