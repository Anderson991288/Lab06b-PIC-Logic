"""M3 s2：用另一種方法檢查最終 GDS。以 Python／Shapely／SciPy 獨立實作「邊對距離」的線寬與間距檢查，與 KLayout DRC 逐項對照。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m3_s2\\independent_drc.py   （約 1 分鐘）
輸入：最終 GDS（M2 s7 交付包的 layout/B7_final.gds）、M2 s6 的 drc_rules_fault.gds 與其 KLayout 報告；規則數值取自 common/pdk.py。
輸出：out/edge_cases.gds、out/edge_cases_drc.lyrdb、out/m3_s2_result.json；course/figures/m3_s2/edge_cases.png、min_spacing.png。

方法（不呼叫 KLayout）：
  1. 同一層的多邊形先合併，外框改成逆時針，內部在每條邊的左側。
  2. 每條邊切成短段，用 KD 樹找出距離不超過搜尋半徑的短段配對，計算兩段的最近點與歐氏距離。
  3. 「線寬」要兩段之間是圖形內部（最近點連線同時指向兩條邊的內側）；「間距」要兩段之間是外部。
  4. 兩條邊反向後的夾角小於 45° 才算面對面（與規則檔的 angle_limit 相同）；同一條邊或相鄰邊（距離 0）不計。
  5. 距離 < 規則值 − 0.001 µm（規則檔的 feature_margin）就是違規；同一對原始邊只算一個標記。
"""
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work"))
sys.path.insert(0, str(ROOT / "work" / "common"))
sys.stdout.reconfigure(encoding="utf-8")
from common import drc  # noqa: E402
from common import gds2png as G  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402

plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT = HERE / "out"
FIG = ROOT / "course" / "figures" / "m3_s2"
OUT.mkdir(exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
FINAL = ROOT / "work" / "m2_s7" / "out" / "PIC_delivery" / "layout" / "B7_final.gds"
FAULT = ROOT / "work" / "m2_s6" / "out" / "drc_rules_fault.gds"
t0 = time.time()

# 規則（µm）：(最小線寬, 最小間距)；與規則檔相同，門檻再減 feature_margin 0.001
RULES = {3: (0.35, 0.20), 4: (0.20, 0.35), 5: (0.25, 0.25), 39: (0.6, 10.0), 41: (2.0, 10.0), 100: (0.25, 0.25)}
MARGIN = 0.001
SEARCH = {3: 1.0, 4: 25.0, 5: 1.0, 39: 15.0, 41: 15.0, 100: 1.0}       # 量測「最小值」的搜尋半徑
ANGLE = 45.0


def layers(gds):
    s, db = G.parse(str(gds))
    ref = {r["sname"] for st in s.values() for r in st["srefs"]}
    tops = [n for n in s if n not in ref]
    pl = []
    for t in tops:
        G.flatten(s, t, np.eye(2), np.zeros(2), pl)
    out = {}
    for l, p in pl:
        g = Polygon(p * db / 1e-6)
        out.setdefault(l, []).append(g if g.is_valid else g.buffer(0))
    return out


def edges_of(polys, piece):
    """合併後每條邊切成 ≤ piece 的短段；回傳 (起點, 終點, 原始邊編號, 原始邊方向)。"""
    u = unary_union(polys)
    gs = list(u.geoms) if hasattr(u, "geoms") else [u]
    A, B, P, D = [], [], [], []
    eid = 0
    for g in gs:
        g = orient(g, sign=1.0)                          # 外框逆時針、孔順時針：內部都在邊的左側
        for ring in [g.exterior, *g.interiors]:
            c = np.asarray(ring.coords)
            for a, b in zip(c[:-1], c[1:]):
                L = float(np.hypot(*(b - a)))
                if L < 1e-9:
                    continue
                n = max(1, int(math.ceil(L / piece)))
                t = np.linspace(0, 1, n + 1)
                pts = a + (b - a) * t[:, None]
                A.append(pts[:-1])
                B.append(pts[1:])
                P.append(np.full(n, eid))
                D.append(np.repeat(((b - a) / L)[None], n, axis=0))
                eid += 1
    if not A:
        return None
    return np.vstack(A), np.vstack(B), np.concatenate(P), np.vstack(D)


def seg_closest(a0, a1, b0, b1):
    """多組線段的最近點（向量化）。"""
    d1, d2, r = a1 - a0, b1 - b0, a0 - b0
    a = (d1 * d1).sum(1)
    e = (d2 * d2).sum(1)
    f = (d2 * r).sum(1)
    c = (d1 * r).sum(1)
    b = (d1 * d2).sum(1)
    den = a * e - b * b
    s = np.where(den > 1e-18, np.clip((b * f - c * e) / np.where(den > 1e-18, den, 1), 0, 1), 0.0)
    t = (b * s + f) / e
    t = np.clip(t, 0, 1)
    s = np.clip((b * t - c) / a, 0, 1)
    p = a0 + d1 * s[:, None]
    q = b0 + d2 * t[:, None]
    return p, q, np.hypot(*(q - p).T)


def check(polys, rule, kind, search=None, angle=ANGLE):
    """kind = 'width' 或 'space'。回傳 (違規標記 [(距離, 點1, 點2)], 量到的最小值, 位置)。"""
    R = max(rule, search or rule)
    piece = max(min(R, 2.0), 0.05)
    E = edges_of(polys, piece)
    if E is None:
        return [], None, None
    A, B, P, D = E
    mid = (A + B) / 2
    pairs = cKDTree(mid).query_pairs(R + piece, output_type="ndarray")
    if len(pairs) == 0:
        return [], None, None
    i, j = pairs[:, 0], pairs[:, 1]
    keep = P[i] != P[j]
    i, j = i[keep], j[keep]
    p, q, d = seg_closest(A[i], B[i], A[j], B[j])
    ni = np.stack([-D[i, 1], D[i, 0]], 1)               # 左側法向量＝指向內部
    nj = np.stack([-D[j, 1], D[j, 0]], 1)
    v = q - p
    sgn = 1 if kind == "width" else -1
    facing = (sgn * (v * ni).sum(1) > 1e-9) & (sgn * (-v * nj).sum(1) > 1e-9)
    cosang = -(D[i] * D[j]).sum(1)                       # 一條邊反向後的夾角
    ok = facing & (d > 1e-6) & (d <= R)
    if angle is not None:
        ok &= cosang > math.cos(math.radians(angle))
    if not ok.any():
        return [], None, None
    d, p, q, pi, pj = d[ok], p[ok], q[ok], P[i][ok], P[j][ok]
    k = int(np.argmin(d))
    found = {}
    for n in np.nonzero(d < rule - MARGIN)[0]:
        key = (min(pi[n], pj[n]), max(pi[n], pj[n]))
        if key not in found or d[n] < found[key][0]:
            found[key] = (float(d[n]), p[n].tolist(), q[n].tolist())
    return list(found.values()), float(d[k]), [p[k].tolist(), q[k].tolist()]


def run_all(gds, angle=ANGLE, measure=True):
    L = layers(gds)
    res = {}
    for l, (w, s) in RULES.items():
        if l not in L:
            continue
        mw = check(L[l], w, "width", SEARCH[l] if measure else None, angle)
        ms = check(L[l], s, "space", SEARCH[l] if measure else None, angle)
        res[l] = dict(width=dict(markers=mw[0], min=mw[1], at=mw[2]), space=dict(markers=ms[0], min=ms[1], at=ms[2]))
    return res


def klayout_markers(lyrdb):
    """KLayout 報告裡每個標記：(類別, 兩條邊的端點, 距離)。"""
    txt = Path(lyrdb).read_text(encoding="utf-8")
    out = []
    for cat, val in re.findall(r"<category>'(.*?)'</category>.*?<value>(.*?)</value>", txt, flags=re.S):
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", val.split(":", 1)[1])]
        if len(nums) == 8:
            a0, a1, b0, b1 = (np.array(nums[k:k + 2])[None] for k in (0, 2, 4, 6))
            _, _, dd = seg_closest(a0, a1, b0, b1)
            out.append((cat.replace("&lt;", "<"), nums, float(dd[0])))
    return out


def rule_of(cat):
    m = re.search(r"\(GDS(\d+)\s*<", cat)
    return (int(m.group(1)), "width" if "feature" in cat else "space") if m else None


# ① 最終 GDS：兩種方法都看違規；獨立方法再量出每層的最小線寬與最小間距
fin = run_all(FINAL)
kl_final = drc.run(FINAL, design_area=(3876.0, 1200.0))
final = {}
for l, r in fin.items():
    final[l] = dict(rule_w=RULES[l][0], rule_s=RULES[l][1],
                    min_w=r["width"]["min"], at_w=r["width"]["at"], n_w=len(r["width"]["markers"]),
                    min_s=r["space"]["min"], at_s=r["space"]["at"], n_s=len(r["space"]["markers"]))
    print("final GDS", l, final[l]["min_w"], final[l]["n_w"], final[l]["min_s"], final[l]["n_s"])
print("KLayout final", kl_final["total"])

# 獨立量測金屬與 heater 的最小間距（不同多邊形之間，Shapely 的多邊形距離，不受夾角限制）
L = layers(FINAL)
poly_gap = {}
for l in (3, 4, 5, 39, 41):
    u = unary_union(L[l])
    gs = list(u.geoms) if hasattr(u, "geoms") else [u]
    best = (math.inf, None)
    for a in range(len(gs)):
        for b in range(a + 1, len(gs)):
            dd = gs[a].distance(gs[b])
            if dd < best[0]:
                best = (dd, [list(gs[a].centroid.coords[0]), list(gs[b].centroid.coords[0])])
    poly_gap[l] = dict(min=best[0], at=best[1], n=len(gs))
print("polygon gaps", {k: round(v["min"], 3) for k, v in poly_gap.items()})

# ② M2 s6 的規則故障注入檔：兩種方法的標記逐一對照
kf = klayout_markers(FAULT.with_name(FAULT.stem + "_drc.lyrdb"))
mine_f = run_all(FAULT, measure=False)
fault_rows = []
for l, (w, s) in RULES.items():
    for kind in ("width", "space"):
        kk = [m for m in kf if rule_of(m[0]) == (l, kind)]
        mm = mine_f.get(l, {}).get(kind, {}).get("markers", [])
        fault_rows.append(dict(layer=l, kind=kind, klayout=len(kk), mine=len(mm),
                               d_klayout=min((m[2] for m in kk), default=None), d_mine=min((m[0] for m in mm), default=None)))
print("fault file", [(r["layer"], r["kind"], r["klayout"], r["mine"]) for r in fault_rows])

# ③ 邊界案例：專門挑兩種方法可能不一致的地方
import ipkiss3.all as i3  # noqa: E402
import pdk  # noqa: E402
T = pdk.pdk.TECH
LAY = {3: pdk.L_WG, 39: pdk.L_HT, 41: pdk.L_PAD}


def tri(apex_deg, h=6.0):
    w = 2 * h * math.tan(math.radians(apex_deg / 2))
    return [(0, -w / 2), (h, 0), (0, w / 2)]


CASES = [  # (代號, 說明, 圖層, 規則種類, 多邊形清單（各自的頂點）, 預期違反規則？)
    ("C1", "線寬 0.300 µm", 3, "width", [[(0, 0), (10, 0), (10, 0.3), (0, 0.3)]], True),
    ("C2", "線寬 0.349 µm（＝門檻）", 3, "width", [[(0, 0), (10, 0), (10, 0.349), (0, 0.349)]], False),
    ("C3", "線寬 0.348 µm", 3, "width", [[(0, 0), (10, 0), (10, 0.348), (0, 0.348)]], True),
    ("C4", "間距 0.199 µm（＝門檻）", 3, "space", [[(0, 0), (5, 0), (5, 1), (0, 1)], [(5.199, 0), (10, 0), (10, 1), (5.199, 1)]], False),
    ("C5", "間距 0.150 µm", 3, "space", [[(0, 0), (5, 0), (5, 1), (0, 1)], [(5.15, 0), (10, 0), (10, 1), (5.15, 1)]], True),
    ("C6", "楔形尖端，頂角 20°", 3, "width", [tri(20)], True),
    ("C7", "楔形尖端，頂角 60°", 3, "width", [tri(60)], None),
    ("C8", "同一圖形內的窄縫 0.15 µm（U 形）", 3, "space",
     [[(0, 0), (6, 0), (6, 3), (3.075, 3), (3.075, 1), (2.925, 1), (2.925, 3), (0, 3)]], True),
    ("C9", "金屬方塊對角，角對角 8.49 µm", 41, "space", [[(0, 0), (20, 0), (20, 20), (0, 20)], [(26, 26), (46, 26), (46, 46), (26, 46)]], None),
    ("C10", "金屬方塊錯開，平行邊距 9 µm、只重疊 2 µm", 41, "space", [[(0, 0), (20, 0), (20, 20), (0, 20)], [(29, 18), (49, 18), (49, 38), (29, 38)]], True),
    ("C11", "TiN 兩條線間距 9.5 µm", 39, "space", [[(0, 0), (30, 0), (30, 1), (0, 1)], [(0, 10.5), (30, 10.5), (30, 11.5), (0, 11.5)]], True),
]
X0 = {}
elems = []
for n, (cid, desc, l, kind, polys, exp) in enumerate(CASES):
    x0 = 80.0 * n
    X0[cid] = x0
    for pts in polys:
        elems.append(i3.Boundary(layer=LAY[l], shape=[(round(x + x0, 3), round(y, 3)) for x, y in pts]))
ec_gds = OUT / "edge_cases.gds"
i3.LayoutCell(name="EDGE_CASES").Layout(elements=elems).write_gdsii(str(ec_gds))
kl = drc.run(ec_gds, design_area=None)
km = klayout_markers(ec_gds.with_name(ec_gds.stem + "_drc.lyrdb"))
mine_a = run_all(ec_gds, angle=ANGLE, measure=False)
mine_n = run_all(ec_gds, angle=None, measure=False)


def in_case(pt, cid):
    return X0[cid] - 20 <= pt[0] <= X0[cid] + 60


case_rows = []
for cid, desc, l, kind, polys, exp in CASES:
    k_hits = [m for m in km if rule_of(m[0]) == (l, kind) and in_case(m[1][:2], cid)]
    a_hits = [m for m in mine_a.get(l, {}).get(kind, {}).get("markers", []) if in_case(m[1], cid)]
    n_hits = [m for m in mine_n.get(l, {}).get(kind, {}).get("markers", []) if in_case(m[1], cid)]
    case_rows.append(dict(id=cid, desc=desc, layer=l, kind=kind, expect=exp,
                          klayout=len(k_hits), mine=len(a_hits), mine_noangle=len(n_hits),
                          d_klayout=min((m[2] for m in k_hits), default=None), d_mine=min((m[0] for m in a_hits), default=None),
                          d_noangle=min((m[0] for m in n_hits), default=None)))
    print(cid, desc, "KL", len(k_hits), "mine", len(a_hits), "no-angle", len(n_hits))

# 圖 1：邊界案例（多邊形＋兩種方法的標記）
fig, axs = plt.subplots(2, 6, figsize=(16, 6))
ec_l = layers(ec_gds)
col = {3: G.LAYER_COLOR[3], 39: G.LAYER_COLOR[39], 41: G.LAYER_COLOR[41]}
for ax, row, case in zip(axs.flat, case_rows, CASES):
    cid, desc, l = case[0], case[1], case[2]
    x0 = X0[cid]
    for g in ec_l.get(l, []):
        if x0 - 5 <= g.bounds[0] <= x0 + 60:
            ax.add_patch(MPoly(np.asarray(g.exterior.coords) - [x0, 0], closed=True, fc=col[l], ec="black", lw=0.4, alpha=0.6))
    for m in km:
        if rule_of(m[0]) == (l, case[3]) and in_case(m[1][:2], cid):
            a = np.array(m[1]).reshape(4, 2) - [x0, 0]
            ax.plot(a[:2, 0], a[:2, 1], color="#b3261e", lw=3, alpha=0.7)
            ax.plot(a[2:, 0], a[2:, 1], color="#b3261e", lw=3, alpha=0.7)
    for m in mine_a.get(l, {}).get(case[3], {}).get("markers", []):
        if in_case(m[1], cid):
            ax.plot([m[1][0] - x0, m[2][0] - x0], [m[1][1], m[2][1]], color="#1f6feb", lw=1.5, marker="o", ms=3)
    ax.autoscale()
    ax.margins(0.15)
    y0, y1 = ax.get_ylim()
    if cid in ("C1", "C2", "C3", "C4", "C5"):           # 細長案例：縱向放大才看得到
        ax.set_ylim(-0.8, 1.8)
        ax.set_aspect("auto")
    else:
        ax.set_aspect("equal")
    ax.set_title(f"{cid}：{desc}\nKLayout {row['klayout']} 個／獨立方法 {row['mine']} 個", fontsize=8.5)
    ax.tick_params(labelsize=7)
axs.flat[-1].axis("off")
axs.flat[-1].text(0.05, 0.6, "紅：KLayout 標記的兩條邊\n藍：獨立方法找到的最近點連線\n數字：各自的標記數", fontsize=10, va="top")
fig.suptitle("邊界案例：兩種方法的標記（回讀 edge_cases.gds 與 KLayout 報告）", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "edge_cases.png", dpi=140, bbox_inches="tight")
plt.close(fig)

# 圖 2：最終 GDS 上量到的最小 Si 線寬與間距位置
Lf = layers(FINAL)
fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
for ax, (l, kind, title) in zip(axs, ((3, "width", "GDS 3 最小線寬"), (3, "space", "GDS 3 最小間距"), (5, "width", "GDS 5 最小線寬"))):
    at = fin[l][kind]["at"]
    c = (np.array(at[0]) + np.array(at[1])) / 2
    span = 3.0
    for g in Lf[l]:
        if g.distance(Polygon([(c[0] - span, c[1] - span), (c[0] + span, c[1] - span), (c[0] + span, c[1] + span), (c[0] - span, c[1] + span)])) < 0.1:
            ax.add_patch(MPoly(np.asarray(g.exterior.coords), closed=True, fc=G.LAYER_COLOR[l], ec="black", lw=0.3, alpha=0.7))
    ax.plot([at[0][0], at[1][0]], [at[0][1], at[1][1]], color="#b3261e", lw=2, marker="o", ms=4)
    ax.set_xlim(c[0] - span, c[0] + span)
    ax.set_ylim(c[1] - span / 2, c[1] + span / 2)
    ax.set_aspect("equal")
    ax.set_title(f"{title}：{fin[l][kind]['min']:.3f} µm（規則 {RULES[l][0 if kind == 'width' else 1]} µm）", fontsize=10)
    ax.set_xlabel("x（µm）")
fig.tight_layout()
fig.savefig(FIG / "min_spacing.png", dpi=140, bbox_inches="tight")
plt.close(fig)

res = dict(step="M3 s2", date="2026-10-31", final_gds=FINAL.name, final_sha256=hashlib.sha256(FINAL.read_bytes()).hexdigest(),
           rules=RULES, margin=MARGIN, angle_limit=ANGLE, final=final, poly_gap=poly_gap,
           klayout_final=dict(total=kl_final["total"], n_rules=len(kl_final["rules"])),
           fault_rows=fault_rows, cases=case_rows, runtime_s=round(time.time() - t0, 1))
(OUT / "m3_s2_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
print("done", res["runtime_s"], "s")
