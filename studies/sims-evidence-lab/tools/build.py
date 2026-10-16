"""Rebuild standalone browser documents from the preserved model fragments."""
from pathlib import Path
import json
from render import export_html

ROOT = Path(__file__).resolve().parents[1]
MODELS = (
    "sims-network",
    "sims-claim-testing",
    "sims-evidence-and-response",
    "sims-repeated-rounds",
)

for name in MODELS:
    export_html(ROOT / "fragments" / f"{name}.html", ROOT / "site" / f"{name}.html", force=True)

# Seed the standalone shell's fallback state. Valid browser-local saved state
# still takes precedence when reopening the same exported document.
snapshot = json.loads((ROOT / "snapshots/latest-run.json").read_text(encoding="utf-8"))
document = (ROOT / "site/sims-repeated-rounds.html").read_text(encoding="utf-8")
marker = "  let state = null;"
if document.count(marker) != 1:
    raise ValueError("Standalone shell changed; cannot safely insert the saved run")
seed = json.dumps(snapshot, ensure_ascii=True, separators=(",", ":")).replace("<", "\\u003c")
document = document.replace(marker, f"  let state = {seed};", 1)
(ROOT / "site/latest-run.html").write_text(document, encoding="utf-8", newline="\n")
print("Built four models and the latest saved-run document.")
