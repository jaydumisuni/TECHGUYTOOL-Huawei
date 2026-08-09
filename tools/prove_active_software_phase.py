from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "manifests" / "active_software_phase.json"


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    script_rel = config.get("proof_script")
    if not isinstance(script_rel, str) or not script_rel.startswith("tools/prove_phase") or not script_rel.endswith(".py"):
        raise SystemExit("active phase proof_script is outside the approved tools/prove_phase*.py surface")
    script = (ROOT / script_rel).resolve()
    tools = (ROOT / "tools").resolve()
    if tools not in script.parents or not script.is_file():
        raise SystemExit("active phase proof script is missing or escapes tools/")
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
    print(f"ACTIVE PHASE PROOF PASS phase={config['phase']} name={config['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
