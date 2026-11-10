"""Run every topic's offline tests:  python run_tests.py   (or: python run_tests.py 03)

Each topic runs in its own process from its own folder, so modules with the
same name (server.py) in different topics never clash.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
topics = sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name[:2].isdigit())
if len(sys.argv) > 1:
    topics = [t for t in topics if t.name.startswith(sys.argv[1])]

failed = []
for topic in topics:
    print(f"\n=== {topic.name}", flush=True)
    code = subprocess.call([sys.executable, "-m", "unittest", "discover", "-v", "-p", "test_*.py"],
                           cwd=topic, env={**os.environ, "GENUI_DELAY": "0"})
    if code:
        failed.append(topic.name)

print("\n" + ("ALL TOPICS PASSED" if not failed else f"FAILED: {', '.join(failed)}"))
sys.exit(1 if failed else 0)
