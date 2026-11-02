# -*- coding: utf-8 -*-
"""
自包含 GDS -> PNG 渲染器（繪製層俯視圖，依 layer 分色）。
M0 s2 引入為共用模組（取自參考實作，未修改演算法）；佈局出圖一律用它。
輸出：指定的 PNG 檔（render(gds, png, title)）。
只需 numpy + matplotlib，不需 IPKISS。
用法: python gds2png.py <in.gds> <out.png> [title]
"""
import sys, struct, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

LAYER_COLOR = {3: "#1f77b4", 4: "#fde68a", 5: "#e377c2", 39: "#ff7f0e", 41: "#2ca02c", 99: "#8c564b", 100: "#7f7f7f"}   # 固定配色：PAD（41）一律綠色

def _real8(b):
    """GDS 8-byte excess-64 浮點 -> float"""
    sign = -1.0 if (b[0] & 0x80) else 1.0
    exp = (b[0] & 0x7F) - 64
    mant = int.from_bytes(b[1:], "big") / float(1 << 56)
    return sign * mant * (16.0 ** exp)

def parse(path):
    data = open(path, "rb").read()
    structs = {}             # name -> dict
    cur = None
    i = 0
    dbunit_m = 1e-9
    el = None                # current element being read
    while i < len(data):
        ln = struct.unpack(">H", data[i:i+2])[0]
        if ln == 0:
            break
        rt, dt = data[i+2], data[i+3]
        code = (rt << 8) | dt
        payload = data[i+4:i+ln]
        if code == 0x0305:   # UNITS: 2 reals (user-in-dbunit, meters-in-dbunit)
            dbunit_m = _real8(payload[8:16])
        elif code == 0x0502:  # BGNSTR
            pass
        elif code == 0x0606:  # STRNAME
            name = payload.split(b"\x00")[0].decode("ascii", "ignore")
            cur = {"boundaries": [], "srefs": []}
            structs[name] = cur
        elif code == 0x0800:  # BOUNDARY
            el = {"kind": "b", "layer": 0, "xy": None}
        elif code == 0x0A00:  # SREF
            el = {"kind": "s", "sname": None, "ox": 0, "oy": 0,
                  "angle": 0.0, "mag": 1.0, "reflect": False}
        elif code == 0x0D02:  # LAYER
            if el: el["layer"] = struct.unpack(">h", payload[:2])[0]
        elif code == 0x1206:  # SNAME
            if el: el["sname"] = payload.split(b"\x00")[0].decode("ascii", "ignore")
        elif code == 0x1A01:  # STRANS
            if el:
                flags = struct.unpack(">H", payload[:2])[0]
                el["reflect"] = bool(flags & 0x8000)
        elif code == 0x1B05:  # MAG
            if el: el["mag"] = _real8(payload[:8])
        elif code == 0x1C05:  # ANGLE
            if el: el["angle"] = _real8(payload[:8])
        elif code == 0x1003:  # XY
            n = len(payload) // 4
            vals = struct.unpack(">%di" % n, payload[:4*n])
            pts = np.array(vals, dtype=float).reshape(-1, 2)
            if el and el["kind"] == "b":
                el["xy"] = pts
            elif el and el["kind"] == "s":
                el["ox"], el["oy"] = pts[0]
        elif code == 0x1100:  # ENDEL
            if el and cur is not None:
                if el["kind"] == "b":
                    cur["boundaries"].append((el["layer"], el["xy"]))
                else:
                    cur["srefs"].append(el)
            el = None
        i += ln
    return structs, dbunit_m

def affine(reflect, angle_deg, mag, ox, oy):
    th = np.deg2rad(angle_deg)
    c, s = np.cos(th), np.sin(th)
    ry = -1.0 if reflect else 1.0
    # p' = R * (mag * (x, ry*y)) + (ox, oy)
    a = mag * c;        b = -mag * s * ry
    cc = mag * s;       d = mag * c * ry
    return np.array([[a, b], [cc, d]]), np.array([ox, oy])

def flatten(structs, name, M, T, out, depth=0):
    if name not in structs or depth > 20:
        return
    st = structs[name]
    for layer, xy in st["boundaries"]:
        p = xy @ M.T + T
        out.append((layer, p))
    for s in st["srefs"]:
        M2, T2 = affine(s["reflect"], s["angle"], s["mag"], s["ox"], s["oy"])
        flatten(structs, s["sname"], M @ M2, M @ T2 + T, out, depth+1)

def render(gds, png, title=None):
    structs, dbunit_m = parse(gds)
    referenced = set()
    for st in structs.values():
        for s in st["srefs"]:
            referenced.add(s["sname"])
    tops = [n for n in structs if n not in referenced] or list(structs)
    top = tops[0]
    polys = []
    flatten(structs, top, np.eye(2), np.zeros(2), polys)
    scale = dbunit_m / 1e-6   # dbunit -> um
    layers = sorted(set(l for l, _ in polys))
    cmap = plt.get_cmap("tab10")
    colors = {l: LAYER_COLOR.get(l, cmap(i % 10)) for i, l in enumerate(layers)}
    # 畫布依佈局長寬比：接近正方形的 die／晶片用方形畫布（顯示面積約為寬版的 2 倍）、圖例分兩列；寬扁佈局維持 14 × 5
    allp = np.vstack([p for _, p in polys]) * (dbunit_m / 1e-6)
    aspect = (allp[:, 0].max() - allp[:, 0].min()) / max(allp[:, 1].max() - allp[:, 1].min(), 1e-9)
    square = aspect < 2.2
    fig, ax = plt.subplots(figsize=(8.5, 8.5 / aspect + 0.6) if square else (14, 5))
    # 一般層：填色；GDS99(design-area 框)：只畫外框線以免蓋住設計
    fill_patches, fill_colors = [], []
    for l, p in polys:
        if l == 99:
            ax.add_patch(Polygon(p * scale, closed=True, fill=False,
                                 edgecolor=colors[l], linewidth=1.4))
        else:
            fill_patches.append(Polygon(p * scale, closed=True))
            fill_colors.append(colors[l])
    pc = PatchCollection(fill_patches, facecolor=fill_colors, edgecolor="black",
                         linewidth=0.15, alpha=0.75)
    ax.add_collection(pc)
    ax.autoscale(); ax.set_aspect("equal")
    ax.set_xlabel("x (um)"); ax.set_ylabel("y (um)")
    if title: ax.set_title(title)
    import matplotlib.patches as mp
    ax.legend([mp.Patch(color=colors[l]) for l in layers],
              [{3: "GDS 3  Si waveguide", 4: "GDS 4  120 nm etch window", 5: "GDS 5  rib protect (100 nm Si)", 39: "GDS 39  heater (HT)", 41: "GDS 41  electrode/pad (PAD)", 99: "GDS 99  die outline", 100: "GDS 100  text label"}.get(l, "GDS layer %d" % l) for l in layers], loc="upper center", bbox_to_anchor=(0.5, 0.0),
              borderaxespad=4.5, ncol=(4 if square else len(layers)), fontsize=9, frameon=False)   # 圖例放在圖框下方，不遮住電路
    fig.tight_layout(); fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("rendered", png, "layers", layers, "polys", len(polys))

if __name__ == "__main__":
    g = sys.argv[1]; p = sys.argv[2]
    t = sys.argv[3] if len(sys.argv) > 3 else None
    render(g, p, t)
