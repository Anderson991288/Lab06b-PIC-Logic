"""M2 s7 Virtuoso／Calibre 段的彙整：讀 EDA_Server 批次產出（out/、out/calibre/），在 Windows 端補 KLayout 對照。

前置：virtuoso.sh 與 calibre.sh 已在 EDA_Server 跑完（見各檔開頭）。
做的事：
  1. Virtuoso：OA 統計、XStream In／Out log 的錯誤與警告數、切塊訊息（XSTRM-275）。
  2. 幾何：簽核版 vs 兩個匯出版，KLayout 逐層 XOR（xor.drc）。
  3. KLayout pre-DRC：簽核版、兩個匯出版、規則故障檔、邊界案例（複製到 out/klayout/ 再跑，不動其他步驟的檔案）。
  4. Calibre：讀 summary 與 ASCII 結果檔，依規則說明對到 KLayout 類別，逐項比較。
  5. 圖：預設匯出把一條彎曲波導切成幾塊、接縫在哪；8191 點匯出維持一塊。
輸出：out/virtuoso_calibre.json、course/figures/m2_s7_chop.png
用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m2_s7\\eda\\compare.py
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "work" / "common"))
import drc  # noqa: E402
import gds2png as G  # noqa: E402
from gds_stats import stats  # noqa: E402

OUT = HERE / "out"
CAL = OUT / "calibre"
KL = OUT / "klayout"
FIG = ROOT / "course" / "figures"
SIGNED = ROOT / "work" / "m2_s6" / "out" / "b7_chip_checked.gds"
FAULT = ROOT / "work" / "m2_s6" / "out" / "drc_rules_fault.gds"
EDGE = ROOT / "work" / "m3_s2" / "out" / "edge_cases.gds"
DIE = (3876.0, 1200.0)
X0 = {f"C{n + 1}": 80.0 * n for n in range(11)}          # m3_s2 邊界案例的擺放位置
CASES = json.loads((ROOT / "work" / "m3_s2" / "out" / "m3_s2_result.json").read_text(encoding="utf-8"))["cases"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log_counts(p):
    t = Path(p).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Translation completed\. '(\d+)' error\(s\) and '(\d+)' warning\(s\)", t)
    chop = re.findall(r"XSTRM-275\).*?vertexes in the 'polygon' with starting point \((-?\d+), (-?\d+)\) on layer '(\d+)' is (\d+)", t)
    return dict(errors=int(m.group(1)), warnings=int(m.group(2)),
                chopped=[dict(start_dbu=[int(a), int(b)], layer=int(l), vertices=int(v)) for a, b, l, v in chop])


# ① Virtuoso
oa = {"shapes": {}}
for line in (OUT / "oa_report.txt").read_text(encoding="utf-8").splitlines():
    k, v = line.split(" ", 1)
    if k == "shapes":
        name, n, mx = v.split()
        oa["shapes"][name] = dict(n=int(n), max_points=int(mx))
    elif k in ("cells", "instances"):
        oa[k] = int(v)
    else:
        oa[k] = v
vir = dict(oa=oa, stream_in=log_counts(OUT / "strmIn.log"), out_default=log_counts(OUT / "strmOut_default.log"),
           out_8191=log_counts(OUT / "strmOut_8191.log"),
           version=re.search(r"(IC\d+\.\d+-64b\.\S+)", (OUT / "virtuoso_inspect.log").read_text(errors="replace")).group(1),
           gds=dict(signed=stats(SIGNED), out_default=stats(OUT / "out_default.gds"), out_8191=stats(OUT / "out_8191.gds")))
print("virtuoso", vir["version"], "in", vir["stream_in"]["errors"], vir["stream_in"]["warnings"],
      "chopped", len(vir["out_default"]["chopped"]), len(vir["out_8191"]["chopped"]))

# ② 幾何 XOR
KLAYOUT = drc.KLAYOUT
geo = {}
for v in ("default", "8191"):
    txt = OUT / f"xor_{v}.txt"
    subprocess.run([str(KLAYOUT), "-b", "-r", str(HERE / "xor.drc"), "-rd", f"a={SIGNED}", "-rd", f"b={OUT / f'out_{v}.gds'}",
                    "-rd", f"out={txt}"], check=True, capture_output=True)
    rows = {}
    for line in txt.read_text().split("\n"):
        if line.strip():
            n, xa, xc, ca, cb, ma, mb, aa, ab = line.split()
            rows[n] = dict(xor_area=float(xa), xor_count=int(xc), polys_a=int(ca), polys_b=int(cb),
                           merged_a=int(ma), merged_b=int(mb), area_a=float(aa), area_b=float(ab))
    geo[v] = rows
print("xor GDS3", geo["default"]["3"]["xor_area"], geo["8191"]["3"]["xor_area"])

# ③ KLayout pre-DRC（複製到 out/klayout/ 再跑）
KL.mkdir(exist_ok=True)
INPUTS = {"signed": (SIGNED, DIE), "virtuoso_default": (OUT / "out_default.gds", DIE), "virtuoso_8191": (OUT / "out_8191.gds", DIE),
          "rule_faults": (FAULT, DIE), "edge_cases": (EDGE, None), "signed_area_wrong": (SIGNED, (DIE[0] - 100.0, DIE[1]))}
kl = {}
for name, (src, area) in INPUTS.items():
    dst = KL / f"{name}.gds"
    shutil.copyfile(src, dst)
    r = drc.run(dst, design_area=area)
    kl[name] = dict(total=r["total"], counts=r["counts"], n_rules=len(r["rules"]), sha256=sha(src))
    print("klayout", name, r["total"], r["counts"])


def kl_markers(lyrdb, full=False):
    """KLayout 標記：(類別, 第一個座標 x µm)；full=True 時回傳 (類別, 全部座標 µm)。"""
    out = []
    for _, el in ET.iterparse(lyrdb, events=("end",)):
        if el.tag.split("}")[-1] == "item":
            c = el.findtext("category").strip("'").replace("&lt;", "<")
            vals = " ".join(v.text or "" for v in el.iter() if v.tag.split("}")[-1] == "value")
            nums = [float(x) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", vals)]
            out.append((c, nums if full else (nums[0] if nums else None)))
            el.clear()
    return out


# 預設匯出的 KLayout 標記：位置（接縫）與模式對照實驗
seam_mk = [m for _, m in kl_markers(KL / "virtuoso_default_drc.lyrdb", full=True)]
seam_sites = []                                   # 1 µm 內的標記算同一個接縫
for m in seam_mk:
    if not any(abs(m[0] - s[0]) < 1 and abs(m[1] - s[1]) < 1 for s in seam_sites):
        seam_sites.append((round(m[0], 1), round(m[1], 1)))
seam_sites.sort()
txt = OUT / "seam_modes.txt"
subprocess.run([str(KLAYOUT), "-b", "-r", str(HERE / "seam_modes.drc"), "-rd", f"input={OUT / 'out_default.gds'}",
                "-rd", f"out={txt}"], check=True, capture_output=True)
modes = {}
for line in txt.read_text().split("\n"):
    s = line.split()
    if len(s) == 3:
        modes.setdefault(s[0], {})[s[1]] = int(s[2])
print("seam markers", len(seam_mk), "sites", len(seam_sites), modes)


# ④ Calibre
svrf = (HERE / "cornerstone_pre_drc.svrf").read_text(encoding="utf-8")
CHECK2CAT = dict(re.findall(r"^(\w+)\s*\{\s*@\s*(.+?)\s*$", svrf, re.M))


def cal_summary(name):
    t = (CAL / f"{name}.drc.summary").read_text(errors="replace")
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"RULECHECK (\w+) \.+ TOTAL Result Count = (\d+)", t)}


def cal_results(name):
    """ASCII 結果檔：每個結果 (規則, 第一個座標 x µm)。"""
    lines = (CAL / f"{name}.drc.results").read_text(errors="replace").splitlines()
    prec = int(lines[0].split()[1])
    out, i, check = [], 1, None
    while i < len(lines):
        s = lines[i].split()
        if len(s) == 1 and s[0] in CHECK2CAT:
            check = s[0]
            ncom = int(lines[i + 1].split()[2])
            i += 2 + ncom
            continue
        if s and s[0] in ("e", "p"):
            n = int(s[2])
            xy = lines[i + 1].split()
            out.append((check, int(xy[0]) / prec))
            i += 1 + n
            continue
        i += 1
    return out


ver = re.search(r"Calibre (v\S+)", (CAL / "signed.calibre.log").read_text(errors="replace"))
cal = {name: dict(counts=cal_summary(name), total=sum(cal_summary(name).values())) for name in INPUTS}
for name in cal:
    print("calibre", name, cal[name]["total"], {k: v for k, v in cal[name]["counts"].items() if v})

# 逐條規則對照（KLayout 類別 ↔ Calibre 規則）
rule_rows = []
for check, cat in CHECK2CAT.items():
    row = dict(check=check, category=cat)
    for name in INPUTS:
        row[f"cal_{name}"] = cal[name]["counts"].get(check, 0)
        row[f"kl_{name}"] = kl[name]["counts"].get(cat, 0)
    rule_rows.append(row)
all_kl_rules = drc.run(KL / "signed.gds", design_area=DIE)["rules"]
not_translated = [r for r in all_kl_rules if r not in CHECK2CAT.values()]

# 邊界案例：每個案例兩個引擎各標幾個
km = kl_markers(KL / "edge_cases_drc.lyrdb")
cm = cal_results("edge_cases")


def case_of(x):
    for cid, x0 in X0.items():
        if x0 - 20 <= x <= x0 + 60:
            return cid
    return None


case_rows = []
for c in CASES:
    cid = c["id"]
    k = sum(1 for cat, x in km if x is not None and case_of(x) == cid)
    m = sum(1 for chk, x in cm if case_of(x) == cid)
    case_rows.append(dict(id=cid, desc=c["desc"], layer=c["layer"], kind=c["kind"], expect=c["expect"],
                          klayout=k, klayout_m3s2=c["klayout"], calibre=m, independent=c["mine"]))
    print(cid, c["desc"], "KL", k, "Calibre", m, "independent", c["mine"])

# ⑤ 圖：被切開的一條曲線
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
plt.rcParams["font.family"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def cell_polys(gds, cell, layer=3):
    st, db = G.parse(str(gds))
    return [xy * db / 1e-6 for l, xy in st[cell]["boundaries"] if l == layer]


cells_max = {}
st_sig, _ = G.parse(str(SIGNED))
for n, s in st_sig.items():
    for l, xy in s["boundaries"]:
        if l == 3:
            cells_max[n] = max(cells_max.get(n, 0), len(xy))
big = max(cells_max, key=cells_max.get)
pd_ = cell_polys(OUT / "out_default.gds", big)
p8 = cell_polys(OUT / "out_8191.gds", big)
bb = np.vstack(p8)
in_cell = [m for m in seam_mk if np.hypot(bb[:, 0] - m[0], bb[:, 1] - m[1]).min() < 1.0]   # 只取落在這條波導上的標記
fig = plt.figure(figsize=(11, 6.4))
gs = fig.add_gridspec(2, 2, width_ratios=[2.3, 1])
ax_d, ax_8, ax_z = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[:, 1])
cols = plt.cm.tab10.colors


def draw(ax, polys, lw=0.3):
    for j, p in enumerate(polys):
        ax.fill(p[:, 0], p[:, 1], color=cols[j % 10], alpha=0.7, lw=0)
        ax.plot(np.r_[p[:, 0], p[0, 0]], np.r_[p[:, 1], p[0, 1]], color="k", lw=lw)


def draw_marks(ax, marks, lw=1.0):
    for m in marks:
        e = np.array(m[:8]).reshape(4, 2)
        ax.plot(e[:2, 0], e[:2, 1], color="r", lw=lw)
        ax.plot(e[2:, 0], e[2:, 1], color="r", lw=lw)


def strokes(ax, polys):
    """波導只有 0.45 µm 寬，整體圖改用粗色線表示每一塊。"""
    for j, p in enumerate(polys):
        ax.plot(p[:, 0], p[:, 1], color=cols[j % 10], lw=5, solid_capstyle="butt")


strokes(ax_d, pd_)
for s in sorted({round(float(p[:, 0].max()), 3) for p in pd_})[:-1]:
    ax_d.axvline(s, color="0.5", lw=0.6, ls=":")
for m in in_cell:
    ax_d.plot(m[0], m[1], "o", ms=11, mfc="none", mec="r", mew=1.5)
ax_d.set_title(f"預設匯出（maxVertices 200）：切成 {len(pd_)} 塊（顏色）；紅圈＝KLayout 線寬標記 {len(in_cell)} 個", fontsize=9.5)
strokes(ax_8, p8)
ax_8.set_title(f"maxVertices 8191：{len(p8)} 塊，KLayout 0 個", fontsize=9.5)
for ax in (ax_d, ax_8):
    ax.set_ylabel("y（µm）")
ax_8.set_xlabel("x（µm）")
zc = np.array(in_cell[0][:2]) if in_cell else bb.mean(0)
draw(ax_z, pd_, lw=0.8)
draw_marks(ax_z, in_cell, 2.0)
ax_z.set_xlim(zc[0] - 0.9, zc[0] + 0.9)
ax_z.set_ylim(zc[1] - 0.9, zc[1] + 0.9)
ax_z.set_aspect("equal")
ax_z.set_title(f"放大：x = {zc[0]:g} µm 的接縫\n兩塊在切線上各形成一個尖角", fontsize=9.5)
ax_z.set_xlabel("x（µm）")
fig.suptitle(f"同一條彎曲波導（{cells_max[big]} 點）由 Virtuoso 匯出後的多邊形", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "m2_s7_chop.png", dpi=130)
plt.close(fig)

res = dict(
    virtuoso=vir, geometry=geo, klayout=kl, calibre=cal, calibre_version=ver.group(1) if ver else None,
    rules=rule_rows, not_translated=not_translated, cases=case_rows,
    chop_figure=dict(cell=big, points=cells_max[big], pieces_default=len(pd_), pieces_8191=len(p8), markers_in_cell=len(in_cell)),
    seam=dict(markers=len(seam_mk), sites=[list(s) for s in seam_sites], modes=modes,
              lengths_um=sorted({round(float(np.hypot(m[2] - m[0], m[3] - m[1])), 3) for m in seam_mk})),
    inputs={k: dict(file=Path(v[0]).name, design_area_um=v[1]) for k, v in INPUTS.items()},
    svrf_sha256=sha(HERE / "cornerstone_pre_drc.svrf"),
)
ok = (vir["stream_in"]["errors"] == vir["stream_in"]["warnings"] == 0
      and all(r["xor_area"] == 0 for r in geo["8191"].values())
      and kl["signed"]["total"] == kl["virtuoso_8191"]["total"] == 0
      and cal["signed"]["total"] == cal["virtuoso_8191"]["total"] == 0
      and all(r["cal_rule_faults"] == r["kl_rule_faults"] for r in rule_rows)
      and cal["signed_area_wrong"]["counts"].get("AREA_99", 0) >= 1)
res["all_ok"] = ok
(OUT / "virtuoso_calibre.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print("all_ok", ok)
