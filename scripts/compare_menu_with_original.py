"""Feed one scripted menu session to the original commit and the current tree; diff output
and the resulting save files. Usage: python scripts/compare_menu_with_original.py [commit]"""

import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

ORIGINAL = sys.argv[1] if len(sys.argv) > 1 else "82ed75e"
SESSION = [
    "1",                                                             # catalog
    "2", "student", "hoodie", "2", "mug", "x", "mug", "1", "", "delivery",  # quote, bad qty
    "3", "", "bag", "2", "", "", "y",                                # place ORD-0001
    "3", "", "mug", "1", "", "", "n",                                # decline placement
    "3", "", "laptop", "1", "", "",                                  # invalid -> error
    "4", "5", "ORD-0001",                                            # history, lookup
    "6", "ORD-0001", "n", "6", "ORD-0001", "y",                      # decline, then cancel
    "9", "5", "ORD-0404",                                            # bad option, bad id
    "0",
]


def run(cwd, data):
    result = subprocess.run([sys.executable, "-m", "supplydesk", "--data", str(data)],
                            cwd=cwd, input="\n".join(SESSION) + "\n",
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout + result.stderr


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    subprocess.run(["git", "worktree", "add", "-q", str(tmp / "orig"), ORIGINAL], check=True)
    try:
        before = run(tmp / "orig", tmp / "a.json")
        after = run(Path.cwd(), tmp / "b.json")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(tmp / "orig")], check=True)
    print(f"original lines: {len(before.splitlines())}, current lines: {len(after.splitlines())}")
    print("orders placed in session:", before.count("ORD-0001 - placed"))
    print("menu output identical:", before == after)
    print("save files identical:", filecmp.cmp(tmp / "a.json", tmp / "b.json", shallow=False))
    if before != after:
        import difflib
        sys.stdout.writelines(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))
