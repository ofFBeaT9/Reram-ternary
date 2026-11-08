"""Do two versions of rtl/tcim_core.sv differ only in the `ifdef FORMAL block and comments? (7 November 2026: the test
benches, mutation tests, equivalence proofs and place and route of revision 4.7 ran on the batch 27 file, md5 d41aed6c; the
properties were restructured afterwards.) Usage: python3 tools/same_logic.py <old.sv> <new.sv> <out.json>"""
import hashlib, json, re, sys
def norm(t):
    a = t.index("`ifdef FORMAL\n"); b = t.rindex("endmodule")
    t = t[:a] + t[b:]
    t = re.sub(r"//[^\n]*", "", t); t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"\s+", " ", t).strip()
o, n = (open(f).read() for f in sys.argv[1:3])
r = dict(old=sys.argv[1], old_md5=hashlib.md5(o.encode()).hexdigest(), new=sys.argv[2], new_md5=hashlib.md5(n.encode()).hexdigest(),
         same_logic_outside_formal_block_and_comments=norm(o) == norm(n))
json.dump(r, open(sys.argv[3], "w"), indent=1); print(r)
sys.exit(0 if r["same_logic_outside_formal_block_and_comments"] else 1)
