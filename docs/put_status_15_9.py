"""Insert or replace section 15.9 of docs/STATUS.md (revision 4.9) with docs/page/lock49_section.py's text (re-runnable)."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docs" / "page"))
import lock49_section
sec = lock49_section.status_md()
p = ROOT / "docs/STATUS.md"; s = p.read_text()
end = s.index("\n---\n\n## Appendix A")
if "### 15.9 " in s:
    s = s[:s.index("### 15.9 ")] + sec.rstrip() + "\n" + s[end:]
else:
    s = s[:end] + "\n" + sec.rstrip() + "\n" + s[end:]
p.write_text(s)
print("15.9 written")
