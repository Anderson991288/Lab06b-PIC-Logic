"""M0 s1（E1）：一顆帶 heater 的 MZI 佈局，驗證 IPKISS＋CORNERSTONE PDK＋KLayout DRC 的整條工具鏈。

改寫自前期課程的 MZI 工具鏈測試件（幾何與故障清單不變）；Lab06b 版的差異：
  - 共用模組改由 work/common 匯入；圖存到 course/figures/m0_s1/。
  - 找不到 KLayout 時不中斷：照樣輸出 GDS、出圖與外框外檢查，DRC 標為 blocked，裝好 KLayout 後重跑即可。


用途：
  1. 以 PDK 標準 2×2 MMI 與 strip 波導組出平衡 MZI：φ 段（外相位）→ MMI → θ 段（內相位）→ MMI。
  2. 兩個 heater（TiN 100 µm）在上臂，各以 Ti/AL 接觸墊直接壓在 TiN 落墊上（無 via），引線到 80×80 µm pad。
  3. 依「配給的區塊尺寸」BLOCK_UM 畫 GDS 99 設計區並傳給 DRC（不由外框回推），跑 DRC 必須 0 違規、外框外無圖形。
  4. 故障注入：另做一份刻意違規的 GDS，每類違規各一個（GDS 3 線寬與間距、GDS 39 線寬與間距、GDS 41 線寬與間距、
     設計區尺寸不符、圖形超出外框），確認每一類都恰好被抓到、沒有多抓（只看 CLEAN 不夠）。
輸入：無（參數寫在本檔開頭，規則引用 common/pdk.py 的 RULES）。
輸出：out/MZI_HT.gds、out/MZI_HT_FAULT.gds、對應 *_drc.lyrdb、out/mzi_drc_result.json；
      course/figures/m0_s1/mzi_layout.png、fault_layout.png。
執行：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s1\\build_mzi_drc.py   （約 10 秒）
"""
import sys
import math
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))     # work/，以便 from common import ...
from common import runtime as rt

rt.setup()
import numpy as np                      # noqa: E402
from ipkiss3 import all as i3           # noqa: E402
from common import pdk                  # noqa: E402
from common import drc                  # noqa: E402
from common import gds2png              # noqa: E402

# ---------------- 幾何參數（µm） ----------------
RAIL_P = 30.0        # 兩臂間距；兩個 heater 不在同一條線上時也遠大於 TiN 間距 10 µm
SB_L = 20.0          # 餘弦 S 彎長
SB_STUB = 0.5        # S 彎兩端的水平短段，避免與相鄰元件之間出現楔形縫
HT_W, HT_L = 0.9, 100.0         # TiN 線寬（MPW #50 建議值，> 0.6 最小線寬）、加熱長
LAND_W, LAND_M = 10.0, 1.0      # TiN 落墊邊長；Ti/AL 接觸墊比落墊每邊多出 1 µm
PS_LEN = HT_L + 2 * (LAND_W + LAND_M)   # 相移段直線長 122
LEAD = 10.0          # 輸入、輸出端的直線引線
WIRE_W = 8.0         # Ti/AL 引線寬（> 2 µm 最小線寬）
PAD = 80.0           # 探針 pad 邊長
WIRE_L = 60.0        # 接觸墊頂端到 pad 底端的引線長
MARGIN = 10.0        # 設計區外框離最外側圖形至少要有的距離（檢查用）
BLOCK_UM = (580.0, 260.0)        # 配給 MZI_HT 的區塊尺寸（設計區），宣告值，不由圖形回推
BLOCK_FAULT_UM = (580.0, 350.0)  # 故障注入版的區塊（多放一排違規圖形）


def r3(v):
    """對齊 1 nm 製造格點。"""
    return round(float(v), 3)


def sbend(x0, y0, y1, L=SB_L, n=41, stub=SB_STUB, snap=True):
    """餘弦 S 彎：y = y0 + (y1−y0)(1−cos πu)/2，u∈[0,1]，兩端各加 stub 水平段。snap＝True 時對齊 1 nm 格點（佈局用）。"""
    u = np.linspace(0, 1, n)
    Lc = L - 2 * stub
    pts = [(x0, y0)] + [(x0 + stub + Lc * t, y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2) for t in u] + [(x0 + L, y1)]
    return [(r3(x), r3(y)) for x, y in pts] if snap else pts


def join(*paths):
    out = []
    for p in paths:
        for q in p:
            if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
                out.append(q)
    return out


def poly_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def min_radius(pts):
    """三點外接圓半徑的最小值（數值曲率半徑）。只能用在未對齊格點的座標：對齊 1 nm 後，二次差分會被格點雜訊放大。"""
    p = np.asarray(pts, float)
    rmin = math.inf
    for a, b, c in zip(p, p[1:], p[2:]):
        ab, bc, ca = np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)
        cross = abs((b - a)[0] * (c - a)[1] - (b - a)[1] * (c - a)[0])
        if cross > 1e-12 and min(ab, bc) > 1e-6:
            rmin = min(rmin, ab * bc * ca / (2 * cross))
    return rmin


def wg(points):
    w = i3.Waveguide(trace_template=pdk.wg_template())
    w.Layout(shape=[(r3(x), r3(y)) for x, y in points])
    return w


def rect(layer, x0, y0, x1, y1):
    return i3.Rectangle(layer=layer, center=(r3((x0 + x1) / 2), r3((y0 + y1) / 2)),
                        box_size=(r3(abs(x1 - x0)), r3(abs(y1 - y0))))


def heater(x0, y, name, ht_w=HT_W):
    """加熱段：TiN 細線（含伸入落墊的部分）、兩端 TiN 落墊、Ti/AL 接觸墊、引線、pad。回傳 (elements, contacts)。"""
    x1 = x0 + HT_L
    el = [rect(pdk.L_HT, x0 - LAND_W, y - ht_w / 2, x1 + LAND_W, y + ht_w / 2)]
    contacts = {}
    for xe, s, tag in ((x0, -1, "a"), (x1, +1, "b")):
        el.append(rect(pdk.L_HT, xe, y - LAND_W / 2, xe + s * LAND_W, y + LAND_W / 2))          # TiN 落墊
        xa0, xa1 = xe, xe + s * (LAND_W + LAND_M)                                                # Ti/AL 接觸墊 11×12
        ya0, ya1 = y - LAND_W / 2 - LAND_M, y + LAND_W / 2 + LAND_M
        el.append(rect(pdk.L_PAD, xa0, ya0, xa1, ya1))
        xc = (xa0 + xa1) / 2
        el.append(rect(pdk.L_PAD, xc - WIRE_W / 2, ya1, xc + WIRE_W / 2, ya1 + WIRE_L))          # 引線往上
        el.append(rect(pdk.L_PAD, xc - PAD / 2, ya1 + WIRE_L, xc + PAD / 2, ya1 + WIRE_L + PAD))  # 探針 pad
        contacts[f"{name}_{tag}"] = (r3(xc), r3(y))
    return el, contacts


def build_mzi(name="MZI_HT", ht_w=HT_W):
    """回傳 (LayoutCell, info)。x＝0 為第一個相移段起點；上臂 y＝+RAIL_P/2。"""
    mmi = pdk.mmi2x2()
    mp = {p.name: (p.position.x, p.position.y) for p in mmi.Layout().ports}
    m_in, m_out, m_py = mp["in2"][0], mp["out2"][0], mp["in2"][1]       # in2／out2 是 +y 側的埠
    yt, yb = RAIL_P / 2, -RAIL_P / 2
    up, lo = [(-LEAD, yt), (PS_LEN, yt)], [(-LEAD, yb), (PS_LEN, yb)]
    elems, insts, contacts, segs = [], [], {}, []
    e, c = heater(LAND_W + LAND_M, yt, "phi", ht_w)
    elems += e
    contacts.update(c)
    x = PS_LEN
    mmi_x = []
    for k in range(2):
        up, lo = join(up, sbend(x, yt, m_py)), join(lo, sbend(x, yb, -m_py))
        segs += [up, lo]
        x += SB_L
        xm = x - m_in
        mmi_x.append(r3(xm))
        insts.append(i3.SRef(reference=mmi, position=(r3(xm), 0.0), name=f"mmi{k + 1}"))
        x = xm + m_out
        up, lo = sbend(x, m_py, yt), sbend(x, -m_py, yb)
        x += SB_L
        if k == 0:
            up.append((x + PS_LEN, yt))
            lo.append((x + PS_LEN, yb))
            e, c = heater(x + LAND_W + LAND_M, yt, "theta", ht_w)
            elems += e
            contacts.update(c)
            x += PS_LEN
    up.append((x + LEAD, yt))
    lo.append((x + LEAD, yb))
    segs += [up, lo]
    insts += [i3.SRef(reference=wg(s)) for s in segs]
    elems.append(i3.PolygonText(layer=pdk.L_LABEL, text=name, coordinate=(r3(x / 2), r3(yb - 25.0)), height=10.0))
    ports = [i3.OpticalPort(name="in0", position=(-LEAD, yt), angle=180.0, trace_template=pdk.wg_template()),
             i3.OpticalPort(name="in1", position=(-LEAD, yb), angle=180.0, trace_template=pdk.wg_template()),
             i3.OpticalPort(name="out0", position=(r3(x + LEAD), yt), angle=0.0, trace_template=pdk.wg_template()),
             i3.OpticalPort(name="out1", position=(r3(x + LEAD), yb), angle=0.0, trace_template=pdk.wg_template())]
    mmi_len = m_out - m_in
    arm_up = sum(poly_len(s) for s in segs[0::2]) + 2 * mmi_len
    arm_lo = sum(poly_len(s) for s in segs[1::2]) + 2 * mmi_len
    sb = sbend(0.0, yt, m_py)
    sb_raw = {n: sbend(0.0, yt, m_py, n=n, snap=False) for n in (41, 201, 1001)}
    info = dict(mmi_ports=mp, mmi_len=mmi_len, mmi_x=mmi_x, length=r3(x + 2 * LEAD),
                path_upper_um=arm_up, path_lower_um=arm_lo, contacts=contacts,
                arm_between_mmi_upper_um=poly_len(segs[2]), arm_between_mmi_lower_um=poly_len(segs[3]),
                sbend_len_um=poly_len(sb),
                sbend_dy=yt - m_py, sbend_Rmin_numeric_snapped=min_radius(sb),
                sbend_Rmin_numeric_raw={str(n): min_radius(v) for n, v in sb_raw.items()},
                sbend_Rmin_analytic=2 * (SB_L - 2 * SB_STUB) ** 2 / (math.pi ** 2 * (yt - m_py)),
                heater_squares=HT_L / ht_w)
    return elems, insts, ports, info


def with_outline(name, elems, insts, ports, block, extra=(), outside=()):
    """GDS 99 設計區＝宣告的區塊尺寸 block，置中於圖形外框；圖形離外框不足 MARGIN 時報錯。
    outside：刻意放在外框外的圖形（故障注入用），不參與置中。"""
    probe = i3.LayoutCell(name=name + "_probe").Layout(elements=list(elems) + list(insts) + list(extra))
    bb = probe.size_info()
    w, h = bb.east - bb.west, bb.north - bb.south
    if w + 2 * MARGIN > block[0] or h + 2 * MARGIN > block[1]:
        raise ValueError(f"{name}：圖形 {w:.1f}×{h:.1f} µm 放不進區塊 {block}（邊距 {MARGIN} µm）")
    cx, cy = round((bb.west + bb.east) / 2), round((bb.south + bb.north) / 2)      # 中心對齊 1 µm
    x0, y0, x1, y1 = cx - block[0] / 2, cy - block[1] / 2, cx + block[0] / 2, cy + block[1] / 2
    outline = rect(pdk.L_OUTLINE, x0, y0, x1, y1)
    cell = i3.LayoutCell(name=name).Layout(elements=list(elems) + list(insts) + list(extra) + list(outside) + [outline],
                                          ports=ports)
    return cell, (x0, y0, x1, y1)


# 故障 → 預期觸發的規則（以 deck 的規則名稱片段比對）
FAULT_RULE = {"F1": "GDS39<600nm", "F2": "GDS41<10micro", "F3": "GDS3< 350nm", "F4": "GDS39<10micro",
              "F5": "design area", "F7": "GDS3<200nm", "F8": "GDS41<2micro"}


def fault_shapes(y_base):
    """刻意違規的圖形，彼此相距 60 µm 以上，各自只觸發一條規則。回傳 (elements, 說明)。F5、F6 另外處理。"""
    R = pdk.RULES
    x = 0.0
    el, expect = [], []
    w = R["HT_min_width"] - 0.1                                                     # F1 TiN 太窄 0.5 µm
    el.append(rect(pdk.L_HT, x, y_base, x + 20, y_base + w)); expect.append(("F1", "GDS 39 線寬 0.5 < 0.6 µm"))
    x += 80
    g = R["PAD_min_gap"] - 4                                                        # F2 AL 間距 6 µm
    el += [rect(pdk.L_PAD, x, y_base, x + 20, y_base + 20), rect(pdk.L_PAD, x + 20 + g, y_base, x + 40 + g, y_base + 20)]
    expect.append(("F2", "GDS 41 間距 6 < 10 µm"))
    x += 110
    w = R["WG_min_width"] - 0.05                                                    # F3 波導太窄 0.30 µm
    el.append(rect(pdk.L_WG, x, y_base, x + 10, y_base + w)); expect.append(("F3", "GDS 3 線寬 0.30 < 0.35 µm"))
    x += 70
    g = R["HT_min_gap"] - 5                                                         # F4 TiN 間距 5 µm
    el += [rect(pdk.L_HT, x, y_base, x + 30, y_base + 2), rect(pdk.L_HT, x, y_base + 2 + g, x + 30, y_base + 4 + g)]
    expect.append(("F4", "GDS 39 間距 5 < 10 µm"))
    x += 90
    g = R["WG_min_gap"] - 0.05                                                      # F7 波導間距 0.15 µm（耦合器的關鍵規則）
    el += [rect(pdk.L_WG, x, y_base, x + 10, y_base + 0.5), rect(pdk.L_WG, x, y_base + 0.5 + g, x + 10, y_base + 1.0 + g)]
    expect.append(("F7", "GDS 3 間距 0.15 < 0.20 µm"))
    x += 70
    w = R["PAD_min_width"] - 0.5                                                    # F8 AL 線寬 1.5 µm
    el.append(rect(pdk.L_PAD, x, y_base, x + 20, y_base + w)); expect.append(("F8", "GDS 41 線寬 1.5 < 2 µm"))
    return el, expect


def main():
    t0 = time.perf_counter()
    od = rt.out_dir(__file__)
    has_kl = Path(drc.KLAYOUT).exists()
    res = {"step": "M0 s1 E1", "date": time.strftime("%Y-%m-%d"), "rules": pdk.RULES,
           "klayout": dict(found=has_kl, exe=Path(drc.KLAYOUT).name),
           "params": dict(RAIL_P=RAIL_P, SB_L=SB_L, HT_W=HT_W, HT_L=HT_L, LAND_W=LAND_W, LAND_M=LAND_M,
                          PS_LEN=PS_LEN, WIRE_W=WIRE_W, PAD=PAD, WG_W=pdk.WG_W, BLOCK_UM=BLOCK_UM)}

    elems, insts, ports, info = build_mzi("MZI_HT")
    cell, box = with_outline("MZI_HT", elems, insts, ports, BLOCK_UM)
    gds = od / "MZI_HT.gds"
    cell.write_gdsii(str(gds))
    res["mzi"] = {k: v for k, v in info.items() if k != "mmi_ports"}
    res["mzi"]["mmi_ports"] = {k: [round(v[0], 3), round(v[1], 3)] for k, v in info["mmi_ports"].items()}
    res["mzi"]["outline_um"] = box
    out1 = drc.outside_outline(gds)                     # 純 Python 回讀 GDS，不需 KLayout
    print(f"MZI_HT：長 {info['length']} µm，MMI 間臂長 上 {info['arm_between_mmi_upper_um']:.3f}／下 "
          f"{info['arm_between_mmi_lower_um']:.3f} µm；外框外 {out1}")

    # 故障注入：F1–F4、F7、F8 圖形；F5 傳入與外框不符的設計區；F6 一個放在外框外的波導
    e2, i2, p2, _ = build_mzi("MZI_HT_FAULT")
    probe = i3.LayoutCell(name="probe_fault").Layout(elements=list(e2) + list(i2)).size_info()
    fel, expect = fault_shapes(probe.south - 50.0)
    f6 = rect(pdk.L_WG, probe.east + 300.0, 0.0, probe.east + 310.0, 0.5)
    cell2, box2 = with_outline("MZI_HT_FAULT", e2, i2, p2, BLOCK_FAULT_UM, extra=fel, outside=[f6])
    expect += [("F5", "設計區宣告 560×350 與外框 580×350 不符"), ("F6", "一個波導圖形在外框外")]
    gds2 = od / "MZI_HT_FAULT.gds"
    cell2.write_gdsii(str(gds2))
    out2 = drc.outside_outline(gds2)
    print(f"MZI_HT_FAULT：外框外 {out2}（預期 1）")

    if has_kl:
        r = drc.run(gds, design_area=BLOCK_UM)
        res["drc_clean"] = dict(status="ran", total=r["total"], counts=r["counts"], n_rules=len(r["rules"]),
                                outside=r["outside"], design_area_um=r["design_area_um"],
                                design_area_source=r["design_area_source"], gds=rt.rel(gds))
        r2 = drc.run(gds2, design_area=(BLOCK_FAULT_UM[0] - 20.0, BLOCK_FAULT_UM[1]))
        hit = {f: sum(n for k, n in r2["counts"].items() if pat in k) for f, pat in FAULT_RULE.items()}
        hit["F6"] = r2["outside"]
        matched = {k for k in r2["counts"] if any(pat in k for pat in FAULT_RULE.values())}
        res["drc_fault"] = dict(status="ran", total=r2["total"], counts=r2["counts"], outside=r2["outside"],
                                expected=expect, hit=hit, all_caught=all(v >= 1 for v in hit.values()),
                                unexpected=sorted(set(r2["counts"]) - matched), gds=rt.rel(gds2))
        # 實際用到的規則：本設計只有 GDS 3、39、41、99、100 五層
        res["rules_relevant"] = [k for k in r["rules"] if any(t in k for t in (
            "GDS3", "GDS39", "GDS41", "GDS100", "design area", "3/0 grid", "39/0 grid", "41/0 grid", "99/0 grid",
            "100/0 grid")) and not any(t in k for t in ("GDS6", "GDS60"))]
        print(f"DRC 正常版 違規 {r['total']}；故障版 各故障 {hit}；意外的規則 {res['drc_fault']['unexpected']}")
    else:
        why = f"找不到 KLayout（{drc.KLAYOUT}）"
        res["drc_clean"] = dict(status="blocked", reason=why, outside=out1, gds=rt.rel(gds))
        res["drc_fault"] = dict(status="blocked", reason=why, outside=out2, expected=expect,
                                hit={"F6": out2}, gds=rt.rel(gds2))
        print("DRC 未執行：" + why)

    t1 = "MZI_HT：平衡 MZI＋兩個 TiN heater" + ("（DRC 0 違規）" if has_kl and res["drc_clean"]["total"] == 0 else "")
    gds2png.render(str(gds), str(rt.fig_path("m0_s1", "mzi_layout.png")), t1)
    gds2png.render(str(gds2), str(rt.fig_path("m0_s1", "fault_layout.png")),
                   "MZI_HT_FAULT：下方故障注入 F1–F4、F7、F8，右側 F6 在外框外")
    res["figs"] = [rt.rel(rt.fig_path("m0_s1", n)) for n in ("mzi_layout.png", "fault_layout.png")]
    res["runtime_s"] = round(time.perf_counter() - t0, 1)
    (od / "mzi_drc_result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float),
                                            encoding="utf-8")
    print("寫出", rt.rel(od / "mzi_drc_result.json"), f"（{res['runtime_s']} s）")


if __name__ == "__main__":
    main()


