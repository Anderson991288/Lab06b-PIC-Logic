"""M2 s4：Layout Review。只讀 GDS（不經 IPKISS 物件），對照規格逐項檢查 B7 核心，並用 M2 s3 的故障版 GDS 驗證每項檢查。

用法：python work\\m2_s4\\review_layout.py   （約 10 秒）
輸入：M2 s3 的 out/b7_core.gds 與 5 個故障版 GDS、out/layout_info.json；spec/pic_spec.json。
輸出：out/review_checks.json；course/figures/m2_s4/review_overview.png、review_zoom.png。
檢查：C1 放置、C2 光學埠、C3 Si 間隙、C4 路徑長（由多邊形面積 ÷ 線寬量出）、C5 heater 對規格通道、
      C6 接觸墊、C7 金屬間距與 heater 到鄰近波導、C8 設計區。GDS 以 SHA-256 記錄版本。
"""
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work" / "common"))
sys.stdout.reconfigure(encoding="utf-8")
import gds2png as G  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Polygon as MPoly, Rectangle  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

S3 = ROOT / "work" / "m2_s3" / "out"
OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m2_s4"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
L_SI, L_HT, L_PAD, L_BOX = 3, 39, 41, 99
WG_W = 0.45
TOL = 1e-3                                   # 1 nm
t0 = time.time()

spec = json.loads((ROOT / "spec" / "pic_spec.json").read_text(encoding="utf-8"))
INFO = json.loads((S3 / "layout_info.json").read_text(encoding="utf-8"))
OPS = [tuple(o) for o in spec["core"]["ops"]]
PITCH = 30.0
L_COL = INFO["geometry"]["column_um"]
RULE = dict(si_gap=0.20, ht_gap=10.0, pad_gap=10.0)          # CORNERSTONE 被動平台規則（與 DRC deck 相同）
CTRL = {(c["mzi"], c["phase"]): c for c in spec["phase_controls"]}


def load(gds):
    """回讀 GDS：回傳 (structs, 縮放, 頂層名, 核心結構名, 核心在頂層的變換)。"""
    structs, db = G.parse(str(gds))
    sc = db / 1e-6
    ref = {s["sname"] for st in structs.values() for s in st["srefs"]}
    top = [n for n in structs if n not in ref][0]
    core = next(n for n, st in structs.items() if any(s["sname"].startswith("MZI_M") for s in st["srefs"]))
    return structs, sc, top, core


def flat(structs, name, M=np.eye(2), T=np.zeros(2)):
    out = []
    G.flatten(structs, name, M, T, out)
    return out


def polys(items, sc, layer):
    ps = []
    for l, p in items:
        if l == layer:
            g = Polygon(p * sc)
            ps.append(g if g.is_valid else g.buffer(0))
    return ps


def sref_tf(s):
    return G.affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])


def review(gds):
    structs, sc, top, core = load(gds)
    allp = flat(structs, top)
    si, ht, pad = polys(allp, sc, L_SI), polys(allp, sc, L_HT), polys(allp, sc, L_PAD)
    outline = polys(allp, sc, L_BOX)
    si_u = unary_union(si)
    res = dict(gds=gds.name, sha256=hashlib.sha256(gds.read_bytes()).hexdigest())

    # C1 放置：核心結構裡的 MZI 參照 vs 規格 OPS
    mz = [s for s in structs[core]["srefs"] if s["sname"].startswith("MZI_M")]
    got = {s["sname"].split("_")[1]: (round(s["ox"] * sc, 3), round(s["oy"] * sc, 3), bool(s["reflect"]), s["angle"]) for s in mz}
    exp = {f"M{k + 1}": (round(lay * L_COL, 3), round(-PITCH * p, 3)) for k, (p, lay) in enumerate(OPS)}
    bad = [k for k in exp if k not in got or got[k][:2] != exp[k] or got[k][2] or got[k][3] != 0]
    res["C1"] = dict(ok=len(mz) == 7 and not bad, n=len(mz), mismatch={k: dict(expect=exp[k], got=got.get(k)) for k in bad})

    # C2 光學埠：埠中心在 Si 上、上下緣在 Si 邊界上、往外 10 nm 已不是 Si（端面）
    pr = []
    for p in INFO["ports"]:
        x, y = p["xy"]
        out_dx = -0.01 if p["angle"] == 180 else 0.01
        ok = (si_u.distance(Point(x, y)) < TOL and si_u.boundary.distance(Point(x, y + WG_W / 2)) < TOL
              and si_u.boundary.distance(Point(x, y - WG_W / 2)) < TOL and not si_u.contains(Point(x + out_dx, y)))
        pr.append(dict(name=p["name"], xy=[x, y], ok=bool(ok)))
    res["C2"] = dict(ok=all(q["ok"] for q in pr), ports=pr)

    # C3 Si：連通區數；彼此不相碰的多邊形之間最小間隙（應 ≥ 0.2 µm）
    comps = list(si_u.geoms) if si_u.geom_type == "MultiPolygon" else [si_u]
    tree = STRtree(si)
    gmin, where = math.inf, None
    for i, g in enumerate(si):
        for j in tree.query(g.buffer(1.0)):
            if j <= i:
                continue
            d = g.distance(si[j])
            if TOL < d < gmin:
                gmin, where = d, [round(c, 2) for c in g.centroid.coords[0]]
    res["C3"] = dict(ok=gmin >= RULE["si_gap"], n_regions=len(comps), min_gap_um=gmin if gmin < math.inf else None, at=where)

    # C4 路徑長：每欄每條 rail（MZI 的上下臂、旁路），長度 = 多邊形面積 ÷ 線寬；MMI 以 Si 外框寬度計
    lengths = {}
    for s in structs[core]["srefs"]:
        M, T = sref_tf(s)
        items = []
        if s["sname"].startswith("MZI_M"):
            k = int(s["sname"].split("_")[1][1:]) - 1
            p, lay = OPS[k]
            ys = {p: -PITCH * p, p + 1: -PITCH * (p + 1)}
            acc = {p: 0.0, p + 1: 0.0}
            for c in structs[s["sname"]]["srefs"]:
                M2, T2 = sref_tf(c)
                sub = [g for g in polys(flat(structs, c["sname"], M @ M2, M @ T2 + T / sc * sc), sc, L_SI)]
                if c["sname"].startswith("MMI"):
                    bx = unary_union(sub).bounds
                    for r in acc:
                        acc[r] += bx[2] - bx[0]
                    continue
                for g in sub:
                    r = min(ys, key=lambda rr: abs(g.centroid.y - (ys[rr] if not c["sname"].startswith("WG") else ys[rr])))
                    yc = g.centroid.y
                    r = p if yc > (ys[p] + ys[p + 1]) / 2 else p + 1
                    acc[r] += g.area / WG_W
            for r, v in acc.items():
                lengths[f"c{lay + 1}r{r}"] = v
        else:
            for g in polys(flat(structs, s["sname"], M, T), sc, L_SI):
                x0, _, x1, _ = g.bounds
                if x1 <= 0 or x0 >= 4 * L_COL:
                    continue                                   # 引線
                lay = int((x0 + 1.0) // L_COL)
                r = int(round(-g.exterior.coords[0][1] / PITCH))
                lengths[f"c{lay + 1}r{r}"] = lengths.get(f"c{lay + 1}r{r}", 0.0) + g.area / WG_W
    ref = INFO["geometry"]["mzi_upper_um"]                     # M2 s3 由中心線算的長度（對照用）
    vals = np.array(list(lengths.values()))
    spread = float(vals.max() - vals.min())
    med = float(np.median(vals))
    worst = max(lengths, key=lambda k: abs(lengths[k] - med))
    res["C4"] = dict(ok=len(lengths) == 20 and spread < 0.01, n=len(lengths), spread_um=spread, median_um=med,
                     centerline_um=ref, lengths=lengths, worst=worst, worst_dev_um=lengths[worst] - med)

    # C5 heater 對規格：每個 TiN 區 → (欄, rail, φ/θ) → 該欄跨這條 rail 的 MZI → 查規格的相位通道
    ht_u = unary_union(ht)
    hts = list(ht_u.geoms) if ht_u.geom_type == "MultiPolygon" else [ht_u]
    found, problems = [], []
    for h in hts:
        cx, cy = h.centroid.coords[0]
        lay, rail = int(cx // L_COL), int(round(-cy / PITCH))
        sec = "phi" if (cx - lay * L_COL) < L_COL / 2 else "theta"
        k = next((i for i, (p, l) in enumerate(OPS) if l == lay and rail in (p, p + 1)), None)
        if k is None:
            problems.append(dict(at=[round(cx, 1), round(cy, 1)], why="不在任何 MZI 上"))
            continue
        c = CTRL[(k + 1, sec)]
        ok = c["rail"] == rail and c["layer"] == lay + 1 and si_u.contains(Point(cx, cy))
        found.append(dict(channel=c["channel"], rail=rail, spec_rail=c["rail"], ok=bool(ok)))
        if not ok:
            problems.append(dict(channel=c["channel"], rail=rail, spec_rail=c["rail"], why="heater 不在規格指定的 rail（上臂）"))
    chans = sorted(f["channel"] for f in found)
    res["C5"] = dict(ok=len(hts) == 14 and not problems and len(set(chans)) == 14, n=len(hts), problems=problems)

    # C6 接觸墊：28 個 Ti/AL 區，每個壓在一個 TiN 區上，每個 TiN 區兩個
    pad_u = unary_union(pad)
    pads = list(pad_u.geoms) if pad_u.geom_type == "MultiPolygon" else [pad_u]
    per = [sum(1 for q in pads if q.intersects(h)) for h in hts]
    orphan = sum(1 for q in pads if not any(q.intersects(h) for h in hts))
    res["C6"] = dict(ok=len(pads) == 28 and all(n == 2 for n in per) and orphan == 0, n=len(pads), orphan=orphan)

    # C7 間距：TiN–TiN、Ti/AL–Ti/AL；TiN（含落墊）到「不在它下面」的波導最短距離（熱串擾的起點，資訊用）
    def min_pair(gs):
        m = math.inf
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                m = min(m, gs[i].distance(gs[j]))
        return m
    d_ht, d_pad = min_pair(hts), min_pair(pads)
    d_nb, nb_at = math.inf, None
    for h in hts:                                              # 「自己」＝經過 heater 那條直線帶的 Si（含接續的 S 彎）
        hx0, _, hx1, _ = h.bounds
        cy = h.centroid.y
        band = box(hx0 - 2, cy - 0.5, hx1 + 2, cy + 0.5)
        for g in si:
            if not g.intersects(band) and g.distance(h) < d_nb:
                d_nb = g.distance(h)
                a, b = nearest_points(h, g)
                nb_at = dict(heater=[round(a.x, 2), round(a.y, 2)], wg=[round(b.x, 2), round(b.y, 2)])
    res["C7"] = dict(ok=d_ht >= RULE["ht_gap"] and d_pad >= RULE["pad_gap"], ht_gap_um=d_ht, pad_gap_um=d_pad,
                     ht_to_other_wg_um=d_nb, ht_to_other_wg_at=nb_at)

    # C8 設計區：所有圖形在 GDS 99 內，尺寸等於宣告
    ob = unary_union(outline).bounds
    others = unary_union(si + ht + pad)
    inside = box(*ob).buffer(TOL).contains(others)
    size = (round(ob[2] - ob[0], 3), round(ob[3] - ob[1], 3))
    res["C8"] = dict(ok=bool(inside) and list(size) == list(INFO["block_um"]), size_um=size, inside=bool(inside))
    res["all_ok"] = all(res[f"C{i}"]["ok"] for i in range(1, 9))
    return res, dict(si=si, ht=hts, pad=pads, outline=ob, comps=comps)


GDS = {"b7_core": S3 / "b7_core.gds"}
FAULTS = {"offset": "M5 往右錯位 0.1 µm", "wrong_rail": "M3 放到 rail 2–3", "flip": "M6 上下翻轉",
          "straight": "旁路改成直線", "arm": "M7 下臂多 2 µm"}
for f in FAULTS:
    GDS[f] = S3 / f"b7_core_{f}.gds"
results, geo = {}, {}
for k, g in GDS.items():
    results[k], geo[k] = review(g)
    print(k, "all_ok", results[k]["all_ok"], {c: results[k][c]["ok"] for c in [f"C{i}" for i in range(1, 9)]})
r0 = results["b7_core"]
print("C3", r0["C3"], "C7", r0["C7"], "C4", r0["C4"]["spread_um"], r0["C4"]["median_um"])

# 圖 1：全圖加註
g0 = geo["b7_core"]


def draw(ax, g, xlim=None, ylim=None, alpha=0.85):
    for layer, gs, col in ((L_SI, g["si"], G.LAYER_COLOR[3]), (L_HT, g["ht"], G.LAYER_COLOR[39]), (L_PAD, g["pad"], G.LAYER_COLOR[41])):
        patches = []
        for q in gs:
            for part in (q.geoms if q.geom_type == "MultiPolygon" else [q]):
                patches.append(MPoly(np.array(part.exterior.coords), closed=True))
        ax.add_collection(PatchCollection(patches, facecolor=col, edgecolor="black", linewidth=0.1, alpha=alpha,
                                          zorder={3: 1, 39: 2, 41: 3}[layer]))
    ob = g["outline"]
    ax.add_patch(Rectangle((ob[0], ob[1]), ob[2] - ob[0], ob[3] - ob[1], fill=False, ec=G.LAYER_COLOR[99], lw=1.2))
    ax.set_aspect("equal")
    ax.set_xlim(*(xlim or (ob[0] - 5, ob[2] + 5)))
    ax.set_ylim(*(ylim or (ob[1] - 5, ob[3] + 5)))
    ax.set_xlabel("x（µm）")
    ax.set_ylabel("y（µm）")


def tag(ax, x, y, n, **kw):
    ax.text(x, y, n, ha="center", va="center", fontsize=10, color="white", weight="bold", zorder=10,
            bbox=dict(boxstyle="circle,pad=0.25", fc="#b3261e", ec="none"), **kw)


fig, ax = plt.subplots(figsize=(15, 3.6))
draw(ax, g0)
for r in range(5):
    ax.text(-75, -PITCH * r, f"{['x1', 'x2', 'x3', 'x4', 'R'][r]} → in{r}", ha="right", va="center", fontsize=8.5)
    ax.text(4 * L_COL + 75, -PITCH * r, f"out{r} → o{r + 1}", va="center", fontsize=8.5,
            color="#0b6b2e" if r in (1, 3) else "#555", weight="bold" if r in (1, 3) else "normal")
for k, (p, lay) in enumerate(OPS):
    ax.add_patch(Rectangle((lay * L_COL + 2, -PITCH * (p + 1) - 6), L_COL - 4, PITCH + 12, fill=False, ec="#2d5a8c", lw=1, ls="--"))
    ax.text(lay * L_COL + L_COL / 2, -PITCH * p + 9, f"M{k + 1}", ha="center", fontsize=9, color="#2d5a8c", weight="bold")
tag(ax, -40, 15, "1")
tag(ax, L_COL / 2 - 110, 15, "2")
tag(ax, L_COL * 1.5, 12, "3")
tag(ax, 4 * L_COL + 40, -PITCH - 14, "4")
tag(ax, 4 * L_COL + 40, -3 * PITCH - 14, "5")
tag(ax, 2 * L_COL, g0["outline"][1] + 8, "6")
ax.set_xlim(-180, 4 * L_COL + 200)
ax.set_title("B7 核心 Review 全圖（回讀 b7_core.gds）", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "review_overview.png", dpi=140, bbox_inches="tight")
plt.close(fig)

# 圖 2：三個放大（M3 的 MMI1 接點、S 彎與旁路間距、φ 段的三個圖層）
x3, y3 = L_COL, -PITCH * 1
xm = x3 + 122 + 20                         # M3 MMI1 輸入端
fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
draw(axs[0], g0, xlim=(xm - 12, xm + 12), ylim=(y3 - 24, y3 - 6))
mmi_y = y3 - PITCH / 2
for dy, n in ((1.015, "in2（上）"), (-1.015, "in1（下）")):
    axs[0].plot([xm], [mmi_y + dy], "o", color="#b3261e", ms=5, zorder=11)
    axs[0].text(xm - 1, mmi_y + dy + (1.2 if dy > 0 else -1.6), n, ha="right", fontsize=9, color="#b3261e")
axs[0].set_title("(a) M3 的 MMI1 輸入端：S 彎接到 PDK 埠", fontsize=10.5)
draw(axs[1], g0, xlim=(x3 + 110, x3 + 160), ylim=(-50, 8))
axs[1].annotate("", xy=(x3 + 150, 0 - 13.985), xytext=(x3 + 150, y3 - 13.985),
                arrowprops=dict(arrowstyle="<->", color="#b3261e"))
axs[1].text(x3 + 151, (-13.985 + y3 - 13.985) / 2, " 30 µm", fontsize=9, color="#b3261e", va="center")
axs[1].text(x3 + 112, 3, "rail 0 旁路往下橫移", fontsize=9)
axs[1].text(x3 + 124, y3 + 3, "M3 上臂往 MMI 收", fontsize=9)
axs[1].set_title("(b) S 彎：旁路與 MZI 上臂一起往下，間距不變", fontsize=10.5)
draw(axs[2], g0, xlim=(x3 - 4, x3 + 24), ylim=(y3 - 9, y3 + 9), alpha=0.6)
axs[2].text(x3 + 12, y3 + 7.5, "Ti/AL 接觸墊 12×12（GDS 41）", fontsize=8.5, ha="center")
axs[2].text(x3 + 13, y3 - 2.2, "TiN 0.9 µm（GDS 39）", fontsize=8.5)
axs[2].text(x3 - 3, y3 - 8, "Si 波導 0.45 µm（GDS 3）", fontsize=8.5)
axs[2].set_title("(c) M3 φ 段起點：三個圖層疊在一起", fontsize=10.5)
fig.tight_layout()
fig.savefig(FIG / "review_zoom.png", dpi=140, bbox_inches="tight")
plt.close(fig)

doc = dict(step="M2 s4", date="2026-10-31", scope="只讀 GDS 與規格的幾何審查；不是 PDK DRC，也不含光學模擬",
           rules=RULE, faults=FAULTS, results=results, runtime_s=round(time.time() - t0, 1))
(OUT / "review_checks.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("done", doc["runtime_s"], "s")
