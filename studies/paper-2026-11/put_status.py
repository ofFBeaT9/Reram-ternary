"""Insert or replace section 15.8 of docs/STATUS.md with the output of status_15_8.py (re-runnable)."""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sec = subprocess.run([sys.executable, str(ROOT / "studies/paper-2026-11/status_15_8.py")], capture_output=True, text=True, check=True).stdout
p = ROOT / "docs/STATUS.md"; s = p.read_text()
end = s.index("\n---\n\n## Appendix A")
if "### 15.8 " in s:
    s = s[:s.index("### 15.8 ")] + sec.rstrip() + "\n" + s[end:]
else:
    s = s[:end] + "\n" + sec.rstrip() + "\n" + s[end:]
p.write_text(s)
print("15.8 written")
