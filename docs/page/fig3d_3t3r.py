"""Fig A' of the page: the next-chip 3T3R one-of-three cell in three dimensions (8 November 2026).

Built from the data of Fig A (the 2T2R cell, base_rev45.html, units of 25 nm) and the 3T3R layout script
(layout/sky130/next_3t3r/cell3.tcl): the cell widens from 3.6 to 5.6 um; the BL- column of Fig A becomes the Z device
(x 2.0 um, as in cell3.tcl) and a copy shifted by 2.0 um becomes the N device (x 4.0 um); the substrate, tie, word line
and source strip are extended; tie contacts are added at the same pitch. The block of JavaScript that draws Fig A is
copied with this data, its own root element, and a lit rule for three devices. Returns (figure html, script block)."""
import copy, json, re

U = 40.0          # units per um in Fig A's data
SHIFT = 2.0 * U   # Z -> N


def build(base):
    i = base.index('const D = {"sol"') + len("const D = ")
    D, end = json.JSONDecoder().raw_decode(base[i:])
    D3 = copy.deepcopy(D)
    sol = []
    tie_contacts = [x for x in D["sol"] if x["mat"] == "licon" and x["path"] is None]
    for x in D["sol"]:
        y = copy.deepcopy(x)
        if x["p"][0] == 0 and abs(x["p"][2] - 144) < 1e-6:            # full-width: substrate, tie, word line, li tie strip
            y["p"][2] = 224
            y["say"] = y["say"].replace("the cell is 3.6 × 3.0 µm", "the cell is 5.6 × 3.0 µm").replace("both select transistors", "all three select transistors")
            sol.append(y)
        elif x["path"] == "s" and x["mat"] == "li1":                    # source strip 0.32 ... 3.28 um -> 0.32 ... 5.28 um
            y["p"][2] = 198.4
            y["say"] = y["say"].replace("joins both sources", "joins the three sources")
            sol.append(y)
        elif x["path"] == "n":                                          # BL- column -> Z, and a copy shifted 2 um -> N
            z = copy.deepcopy(x); z["path"] = "z"
            z["say"] = z["say"].replace("BL− ReRAM", "Z ReRAM").replace("BL− transistor", "Z transistor").replace("BL−", "BLZ")
            sol.append(z)
            n = copy.deepcopy(x); n["p"][0] += SHIFT
            sol.append(n)
        else:
            sol.append(y)
    pitch = tie_contacts[1]["p"][0] - tie_contacts[0]["p"][0]
    xlast = max(t["p"][0] for t in tie_contacts)
    k = 1
    while xlast + k * pitch + tie_contacts[0]["p"][2] <= 216.0 + 1e-6:   # mvpsc of cell3.tcl ends at 5.40 um
        t = copy.deepcopy(tie_contacts[0]); t["p"][0] = xlast + k * pitch; sol.append(t); k += 1
    D3["sol"] = sol
    D3["cell"] = [224, 120]
    D3["cellPlan"]["w"] = 224
    D3["states"] = [
        {"w": "+1", "p": True, "n": False, "z": False, "text": "+1 · bits P 1, Z 0, N 0",
         "long": "Weight +1: the P device is set (low resistance), Z and N are reset. Exactly one device of every weight draws a read current above the reference."},
        {"w": "0", "p": False, "n": False, "z": True, "text": "0 · bits P 0, Z 1, N 0",
         "long": "Weight 0: the Z device is set, P and N reset. A zero weight draws the same read current as a non-zero one, so the row's supply current does not show how many weights are zero."},
        {"w": "−1", "p": False, "n": True, "z": False, "text": "−1 · bits P 0, Z 0, N 1",
         "long": "Weight −1: the N device is set, P and Z reset. Any other combination of sense bits is an invalid code and sets WERR."}]
    data = json.dumps(D3, ensure_ascii=False, separators=(",", ":"))
    # the JavaScript block of Fig A
    a = base.rfind("\n{", 0, i) + 1
    b = base.index("\nshow(0);\n}", i) + len("\nshow(0);\n}")
    js = base[a:b]
    js = js.replace('[data-fig="cell2t2r"]', '[data-fig="cell3t3r"]')
    js = js[:js.index("const D = ") + len("const D = ")] + data + js[js.index("const D = ") + len("const D = ") + end:]
    js = js.replace("return s.path === 'p' ? st.p : s.path === 'n' ? st.n : s.path === 's' ? st.p || st.n : false;",
                    "return s.path === 'p' ? st.p : s.path === 'n' ? st.n : s.path === 'z' ? st.z : s.path === 's' ? st.p || st.n || st.z : false;")
    assert "st.z" in js and '[data-fig="cell3t3r"]' in js
    # the figure container of Fig A
    c = base.index('<div class="iso iso-embed" data-fig="cell2t2r">')
    depth, e = 0, c
    for m in re.finditer(r"<div\b|</div>", base[c:]):
        depth += 1 if m.group(0).startswith("<div") else -1
        if depth == 0:
            e = c + m.end(); break
    html = base[c:e].replace('data-fig="cell2t2r"', 'data-fig="cell3t3r"')
    html = html.replace('data-corner="fig">Fig A<', 'data-corner="fig">Fig A′<').replace(">One weight, oxide removed<", ">Next chip: one 3T3R weight<")
    html = html.replace("+1 · bits 1 0</span>", "+1 · bits P 1, Z 0, N 0</span>").replace('aria-label="2T2R cell in 3D', 'aria-label="3T3R cell in 3D')
    html = html.replace("The two ReRAM devices, 0.26 µm square, under the metal2 bit lines", "The three ReRAM devices, 0.26 µm square, under the metal2 bit lines")
    html = re.sub(r'<span class="iso-caption">.*?</span>',
                  '<span class="iso-caption">The next-chip cell, drawn from its layout script (<code>layout/sky130/next_3t3r/cell3.tcl</code>, 5.6 × 3.0 µm) '
                  'with the same layer heights as Fig A; only the oxide is left out. P, Z and N each have a select transistor, a ReRAM device and a '
                  'metal2 bit line; the word line, the source strip and the source line are shared. Exactly one device is set for every weight, so '
                  'every row of the array holds 24 set devices whatever the weights.</span>', html, flags=re.S)
    assert html.count('data-fig="cell3t3r"') == 1
    return html, js
