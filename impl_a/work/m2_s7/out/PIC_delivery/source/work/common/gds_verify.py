"""只讀 GDS 的連接檢查（M2 s6 起使用；交付包的 verify_gds.py 也用它）。不需要 IPKISS，只用 numpy、shapely 與 gds2png。

optical_lvs(gds, spec, netlist)：GDS 3／5 中高約 6 µm、填滿外框的矩形是 MMI 本體，其餘 Si 連成「導線」；
  每條導線兩端各接一個 MMI 埠（左／右 = in／out，上／下 = 2／1）或晶片端面。兩條導線同時連 A 的 out2→B 的 in2、
  A 的 out1→B 的 in1，A、B 就是一顆 MZI；依 MMI 位置對規格 OPS 命名，重建連接表與 heater 通道後和規格比對。
electrical(gds, spec, pads)：GDS 41 連通網、80 × 80 µm 接墊、GDS 39 heater；heater 位置 → 規格通道；
  每個 heater 必須只接自己的訊號接墊與一個回流網。pads 為 [{name, xy}]（接墊對照表）。
座標約定與 B7 佈局相同：第 c 欄從 x = 489·c 開始，rail r 的 y = −30·r。
"""
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

import gds2png as G

L_COL, PITCH, TOL = 489.0, 30.0, 2e-3


def polys(gds):
    """頂層攤平後的多邊形 [(layer, 座標 µm)]。"""
    structs, db = G.parse(str(gds))
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in ref][0]
    pl = []
    G.flatten(structs, top, np.eye(2), np.zeros(2), pl)
    return [(l, p * (db / 1e-6)) for l, p in pl]


def parts(g):
    return [] if g.is_empty else (list(g.geoms) if hasattr(g, "geoms") else [g])


def _spec(spec):
    ops = [tuple(o) for o in spec["core"]["ops"]]
    ctrl = {(c["mzi"], c["phase"]): c["channel"] for c in spec["phase_controls"]}
    return ops, ctrl


def optical_lvs(gds, spec, netlist):
    OPS, CTRL = _spec(spec)
    pl = polys(gds)
    si = [Polygon(p) for l, p in pl if l in (3, 5)]
    outline = unary_union([Polygon(p) for l, p in pl if l == 99]).bounds

    def is_body(g):                                    # MMI 本體：高約 6 µm 的矩形（彎曲波導的外框也可能很大，所以要求填滿外框）
        x0, y0, x1, y1 = g.bounds
        return (y1 - y0) > 5.5 and (x1 - x0) > 30 and g.area > 0.99 * (x1 - x0) * (y1 - y0)
    bodies = [g for g in si if is_body(g)]
    wires = parts(unary_union([g for g in si if g not in bodies]))
    tin = parts(unary_union([Polygon(p) for l, p in pl if l == 39]))
    problems, term, marks = [], [], 0
    for w in wires:                                    # 每條導線的端點：接到哪個 MMI 埠或哪個端面
        if w.area < 20:
            marks += 1                                 # EC 的研磨刻度（1 × 5、1 × 10 µm 的 GDS 3 方塊）
            continue
        t = []
        for i, b in enumerate(bodies):
            if w.distance(b) < TOL:
                c = w.intersection(b.buffer(TOL)).centroid
                bx, by = b.centroid.coords[0]
                t.append((i, ("in" if c.x < bx else "out") + ("2" if c.y > by else "1")))
        x0, y0, x1, y1 = w.bounds
        if abs(x0 - outline[0]) < TOL:
            t.append(("L", round((y0 + y1) / 2, 1)))
        if abs(x1 - outline[2]) < TOL:
            t.append(("R", round((y0 + y1) / 2, 1)))
        if len(t) != 2:
            problems.append(f"一條導線接了 {len(t)} 個端點（應為 2），位置約 ({w.centroid.x:.0f}, {w.centroid.y:.0f})")
        term.append((w, t))
    link = {}
    for w, t in term:
        if len(t) == 2:
            link[t[0]], link[t[1]] = t[1], t[0]
    mzis = []
    for a in range(len(bodies)):                       # MMI → MZI
        up, lo = link.get((a, "out2")), link.get((a, "out1"))
        if up and lo and up[0] == lo[0] and isinstance(up[0], int) and up[1] == "in2" and lo[1] == "in1":
            mzis.append((a, up[0]))
        elif up and lo and up[0] == lo[0] and isinstance(up[0], int):
            problems.append(f"MMI 之間上下臂交叉（{up[1]}、{lo[1]}）")
    name = {}
    for a, b in mzis:                                  # MZI 命名：MMI1 本體的 x → 欄，中心 y → rail p
        bx, by = bodies[a].centroid.coords[0]
        col, p = int(bx // L_COL), int(round((-by - PITCH / 2) / PITCH))
        k = next((i for i, (pp, l) in enumerate(OPS) if l == col and pp == p), None)
        if k is None:
            problems.append(f"在第 {col + 1} 欄、rail {p} 找到 MZI，但規格沒有")
            continue
        name[a], name[b] = (f"M{k + 1}", "A"), (f"M{k + 1}", "B")
    port = {}
    for i, (nm, ab) in name.items():
        for mp, lp in (("in2", "in0"), ("in1", "in1")) if ab == "A" else (("out2", "out0"), ("out1", "out1")):
            port[(i, mp)] = f"{nm}:{lp}"
    links, ext = [], {}
    Ls = sorted({t[1] for _, tt in term for t in tt if t[0] == "L"}, reverse=True)
    Rs = sorted({t[1] for _, tt in term for t in tt if t[0] == "R"}, reverse=True)
    for w, t in term:
        if len(t) != 2:
            continue
        ends = [f"in{Ls.index(e[1])}" if e[0] == "L" else f"out{Rs.index(e[1])}" if e[0] == "R"
                else port.get(e, f"MMI{e[0]}:{e[1]}") for e in t]
        a, b = ends
        if ":" in a and ":" in b:
            if a.split(":")[1].startswith("in"):
                a, b = b, a
            if not a.startswith("MMI") and a.split(":")[0] != b.split(":")[0]:
                links.append([a, b])
        else:
            m, f = (a, b) if ":" in a else (b, a)
            ext[m] = f
    heater = {}
    for h in tin:                                      # heater：壓在 MZI 上臂輸入（φ）或兩個 MMI 之間的上臂（θ）
        ch = None
        for t in [t for w, t in term if w.intersects(h)]:
            for e in t:
                if isinstance(e[0], int) and e in port and port[e].endswith(":in0"):
                    ch = (port[e].split(":")[0], "phi")
            if ch is None:
                a_ = [e for e in t if isinstance(e[0], int) and name.get(e[0], ("", ""))[1] == "A" and e[1] == "out2"]
                if a_:
                    ch = (name[a_[0][0]][0], "theta")
        if ch is None:
            problems.append(f"heater 在 ({h.centroid.x:.0f}, {h.centroid.y:.0f}) 不在任何 MZI 的上臂")
            continue
        heater[f"{ch[0]}_{ch[1]}"] = [round(h.centroid.x, 1), round(h.centroid.y, 1)]
    key = lambda L: sorted(map(tuple, L))  # noqa: E731
    ok_links, ok_ext = key(links) == key(netlist["links"]), ext == netlist["external"]
    ok_heat = sorted(heater) == sorted(CTRL.values())
    if not ok_links:
        problems.append("MZI 之間的連線與規格不同")
    if not ok_ext:
        problems.append("晶片端面到 MZI 的對應與規格不同")
    if not ok_heat:
        problems.append(f"heater 通道與規格不同（找到 {len(heater)} 個）")
    return dict(ok=not problems, n_bodies=len(bodies), n_wires=len(term), n_marks=marks, n_mzi=len(mzis),
                n_links=len(links), n_ext=len(ext), n_heaters=len(heater), links_match=ok_links, ext_match=ok_ext,
                heaters_match=ok_heat, problems=problems), dict(bodies=bodies, term=term, name=name, links=links)


def electrical(gds, spec, pads):
    OPS, CTRL = _spec(spec)
    pl = polys(gds)
    metal = [Polygon(p) for l, p in pl if l == 41]
    nets = parts(unary_union(metal))
    tin = parts(unary_union([Polygon(p) for l, p in pl if l == 39]))
    sq = []
    for h in tin:                                      # 加熱絲：TiN 扣掉兩端 10 µm 落墊；量測窗離開落墊各 1 µm
        x0, y0, x1, y1 = h.bounds
        L = x1 - x0 - 2 * 10.0 - 2.0
        core = h.intersection(box(x0 + 11, (y0 + y1) / 2 - 2, x1 - 11, (y0 + y1) / 2 + 2))
        w = core.area / L if L > 0 else 0
        sq.append((x1 - x0 - 20) / w if w > 0 else 0)
    pad_poly = [q for q in metal if abs(q.area - 6400) < 1]
    at = {(round(p["xy"][0], 1), round(p["xy"][1], 1)): p["name"] for p in pads}
    net_of = lambda g: next(i for i, n in enumerate(nets) if n.intersects(g))  # noqa: E731
    pad_net = {at.get((round(q.centroid.x, 1), round(q.centroid.y, 1)), "?"): net_of(q) for q in pad_poly}
    h_net = {}
    for h in tin:                                      # heater 通道：位置 → (欄, rail, φ／θ) → 規格
        cx, cy = h.centroid.coords[0]
        col, rail = int(cx // L_COL), int(round(-cy / PITCH))
        sec = "phi" if cx - col * L_COL < L_COL / 2 else "theta"
        k = next(i for i, (p, l) in enumerate(OPS) if l == col and rail in (p, p + 1))
        h_net[CTRL[(k + 1, sec)]] = sorted({i for i, n in enumerate(nets) if n.intersects(h)})
    gnd = {pad_net.get("GND_T"), pad_net.get("GND_B")}
    rows, problems = [], []
    for ch in sorted(CTRL.values()):
        nets_h = h_net.get(ch, [])
        sig = [n for n in nets_h if n not in gnd]
        sig_pads = [p for p, i in pad_net.items() if sig and i == sig[0]]
        g = [n for n in nets_h if n in gnd]
        ok = len(nets_h) == 2 and len(sig) == 1 and len(g) == 1 and sig_pads == [ch]
        rows.append(dict(channel=ch, signal_pad=sig_pads, ground=[k for k in ("GND_T", "GND_B") if pad_net.get(k) in g], ok=ok))
        if not ok:
            problems.append(f"{ch}：金屬網 {len(nets_h)} 個，訊號接墊 {sig_pads}，回流 {rows[-1]['ground']}")
    shared = [p for p, i in pad_net.items() if sum(1 for j in pad_net.values() if j == i) > 1]
    if shared:
        problems.append(f"接墊共用同一金屬網（短路）：{sorted(shared)}")
    return dict(ok=not problems, n_nets=len(nets), n_pads=len(pad_poly), rows=rows, problems=problems,
                heater_squares=[round(float(min(sq)), 2), round(float(max(sq)), 2)])
