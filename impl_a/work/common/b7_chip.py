"""B7 晶片佈局（M2 s5 起使用）：M2 s3 的 B7 核心原樣放入，加上 10 個邊緣耦合器（EC）、扇入／扇出、
14 路 heater 訊號接墊與兩條回流匯流排。

用途：產生晶片 cell（可寫 GDS），光路連接由佈局抽出（i3.NetlistFromLayout），電路由抽出的連接組成。
輸入：B7Core cell（相位 0 寫 GDS；帶相位做電路模擬）、femwell 的 n_eff、n_g。
輸出：無檔案；Chip cell，plan() 回傳 EC、扇入、接墊、金屬線的設計表（供 chip_info.json 與檢查）。

座標沿用核心：rail r 的 y = −30·r；核心輸入埠 x = −60、輸出埠 x = 2016。
光學：EC 間距 250 µm（光纖陣列），端面在晶片左右邊；扇入每條加升餘弦凸起，讓 5 條輸入路徑等長。
電氣：只有一層金屬（GDS 41 Ti/AL），金屬之間不能交越。上兩條 rail（0、1）的 heater 往上接，下兩條（2、3）往下接；
     每個 heater 一端是訊號（接獨立接墊），另一端是回流（接接墊列外側的匯流排），所以訊號線與回流線不交越。
EC 幾何（GDS 3／4／5）：0.25 µm 寬、100 nm 厚的薄矽尖端（GDS 5 最小線寬），漸寬到 1 µm，再在 30 µm 內轉回 0.45 µm strip。
"""
import math

import ipkiss3.all as i3
import numpy as np

import b7_layout as BL
import pdk

T = pdk.pdk.TECH
L_HOLE, L_SLAB = T.PPLAYER.WG_HOL, T.PPLAYER.SLAB          # GDS 4（120 nm 蝕刻窗，暗場）、GDS 5（保護 100 nm 薄矽，亮場）

EC = dict(tip_w=0.25, base_w=1.0, core_end_w=0.35, tip_len=30.0, taper_len=200.0, bilevel_len=30.0, win_half=10.0)
EC_LEN = EC["tip_len"] + EC["taper_len"] + EC["bilevel_len"]          # 260
FIBER_PITCH = 250.0
FAN_L = 480.0                 # 扇入／扇出 S 彎的水平跨度
BUMP_L = 320.0                # 等長凸起所在的直線段
CORE_IN, CORE_OUT = -BL.LEAD, 4 * BL.L_COL + BL.LEAD             # −60、2016
X_LEFT = CORE_IN - FAN_L - BUMP_L - EC_LEN                        # 左端面 −1120
X_RIGHT = CORE_OUT + FAN_L + EC_LEN                               # 右端面 2756
Y_MID = -2 * BL.PITCH                                             # 五條 rail 的中心 −60
DIE_H = 1200.0
DIE = (X_RIGHT - X_LEFT, DIE_H)
Y_DIE = (Y_MID - DIE_H / 2 + 10.0, Y_MID + DIE_H / 2 + 10.0)      # −650、550

# 金屬（µm）
W_LINE, PAD, BUS_W = 8.0, 80.0, 20.0
TOP_PAD_Y, TOP_BUS_Y = 200.0, 300.0
BOT_PAD_Y, BOT_BUS_Y = -320.0, -420.0
CONTACT_HALF = BL.LAND_W / 2 + BL.LAND_M                           # 接觸墊半高 6


def ec_y(k):
    return Y_MID + FIBER_PITCH * (2 - k)


def sbend_l(x0, y0, y1, L, n=161, stub=0.5):
    u = np.linspace(0, 1, n)
    lc = L - 2 * stub
    pts = [(x0, y0)] + [(x0 + stub + lc * t, y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2) for t in u] + [(x0 + L, y1)]
    return [(BL.r3(x), BL.r3(y)) for x, y in pts]


def bump_pts(x0, y0, length, h, n=201):
    u = np.linspace(0, 1, n)
    lb = length - 2.0
    return ([(BL.r3(x0), BL.r3(y0))] + [(BL.r3(x0 + 1.0 + lb * t), BL.r3(y0 + h * (1 - math.cos(2 * math.pi * t)) / 2))
                                        for t in u] + [(BL.r3(x0 + length), BL.r3(y0))])


def fanin_points(k, matched=True):
    """第 k 條輸入：EC 出口 (X_LEFT+EC_LEN, ec_y) → 直線段（等長凸起）→ S 彎 → 核心輸入埠 (−60, −30k)。"""
    x0, y0, y1 = X_LEFT + EC_LEN, ec_y(k), -BL.PITCH * k
    sb = sbend_l(x0 + BUMP_L, y0, y1, FAN_L)
    target = max(BL.poly_len(sbend_l(0, ec_y(j), -BL.PITCH * j, FAN_L)) for j in range(5))
    need = target - BL.poly_len(sb)
    if not matched or need < 1e-6:
        st = [(BL.r3(x0), BL.r3(y0)), (BL.r3(x0 + BUMP_L), BL.r3(y0))]
    else:
        lo, hi = 0.0, 200.0
        for _ in range(60):
            h = (lo + hi) / 2
            lo, hi = (h, hi) if BL.poly_len(bump_pts(x0, y0, BUMP_L, h)) - BUMP_L < need else (lo, h)
        st = bump_pts(x0, y0, BUMP_L, h)
    return BL.join(st, sb)


def fanout_points(k):
    """第 k 條輸出：核心輸出埠 (2016, −30k) → S 彎 → EC 出口 (X_RIGHT−EC_LEN, ec_y)。輸出只量功率，不需等長。"""
    return sbend_l(CORE_OUT, -BL.PITCH * k, ec_y(k), FAN_L)


class ECModel(i3.CompactModel):
    """EC 的電路替身：寬頻、無反射；穿透 t（預設 1，損耗另計），相位以 strip 等長近似。"""
    parameters = ["t", "length", "n_eff", "n_g", "wl0"]
    terms = [i3.OpticalTerm(name="facet"), i3.OpticalTerm(name="out")]

    def calculate_smatrix(parameters, env, S):
        wl = env.wavelength
        n = parameters.n_eff + (parameters.n_eff - parameters.n_g) * (wl - parameters.wl0) / parameters.wl0
        v = parameters.t * np.exp(1j * 2 * np.pi * n * parameters.length / wl)
        S["facet", "out"] = v
        S["out", "facet"] = v


class EdgeCoupler(i3.PCell):
    """薄矽尖端邊緣耦合器：facet 在 x = 0（朝西，光纖側），out 在 x = 260（朝東，接 0.45 µm strip）。"""
    t = i3.NumberProperty(default=1.0)
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)

    class Layout(i3.LayoutView):
        def _generate_elements(self, elems):
            x1, xb = EC["tip_len"], EC["tip_len"] + EC["taper_len"]
            xe = xb + EC["bilevel_len"]
            t, b, w = EC["tip_w"] / 2, EC["base_w"] / 2, pdk.WG_W / 2
            elems += i3.Boundary(layer=L_SLAB, shape=[(0, -t), (x1, -t), (xb, -b), (xe, -w), (xe, w), (xb, b), (x1, t), (0, t)])
            ce = EC["core_end_w"] / 2
            elems += i3.Boundary(layer=pdk.L_WG, shape=[(xb, -ce), (xe, -w), (xe, w), (xb, ce)])
            elems += i3.Rectangle(layer=L_HOLE, center=(xb / 2, 0.0), box_size=(xb, 2 * EC["win_half"]))
            y0 = EC["win_half"] + 6.0                       # 研磨刻度（GDS 3）：每 10 µm 一條，x = 0 加長
            for k, x in enumerate(np.arange(0.0, x1 + 0.1, 10.0)):
                h = 10.0 if k == 0 else 5.0
                for s in (1, -1):
                    elems += i3.Rectangle(layer=pdk.L_WG, center=(max(float(x), 0.5), s * (y0 + h / 2)), box_size=(1.0, h))
            return elems

        def _generate_ports(self, ports):
            tt = pdk.wg_template()
            ports += i3.OpticalPort(name="facet", position=(0.0, 0.0), angle=180.0, trace_template=tt)
            ports += i3.OpticalPort(name="out", position=(EC_LEN, 0.0), angle=0.0, trace_template=tt)
            return ports

    class Netlist(i3.NetlistView):
        def _generate_terms(self, terms):
            terms += i3.OpticalTerm(name="facet")
            terms += i3.OpticalTerm(name="out")
            return terms

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return ECModel(t=self.cell.t, length=EC_LEN, n_eff=self.cell.n_eff, n_g=self.cell.n_g, wl0=1.55)


def plan(ops, contacts, fault="none"):
    """金屬與接墊的設計表。contacts：{通道: [[x, y] 左, [x, y] 右]}（M2 s3 layout_info 的接觸墊中心）。
    規則：φ 段 左＝訊號、右＝回流；θ 段 左＝回流、右＝訊號（同一顆 MZI 的兩條回流線相鄰，訊號接墊在外側）。
    回傳 dict(lines, pads, buses)；lines 每筆 (x, y0, y1, net)，pads 每筆 (名稱, x, y, net)。"""
    lines, pads = [], []
    side = {}
    for ch, (left, right) in contacts.items():
        k = int(ch.split("_")[0][1:]) - 1
        p = ops[k][0]
        up = p <= 1
        side[ch] = "top" if up else "bottom"
        sig, gnd = (left, right) if ch.endswith("phi") else (right, left)
        y_c = sig[1]
        if up:
            ys0, ys1, yg1 = y_c, TOP_PAD_Y - PAD / 2, TOP_BUS_Y - BUS_W / 2
        else:
            ys0, ys1, yg1 = y_c, BOT_PAD_Y + PAD / 2, BOT_BUS_Y + BUS_W / 2
        if fault == "open" and ch == "M4_theta":
            ys0 = y_c + (CONTACT_HALF + 2.0)                                    # 訊號線停在接觸墊外 2 µm
        if fault == "short" and ch == "M3_phi":
            ys1 = TOP_BUS_Y                                                     # 訊號線一路畫到回流匯流排
        lines.append((sig[0], ys0, ys1, ch))
        lines.append((gnd[0], y_c, yg1, "GND_T" if up else "GND_B"))
        pads.append((ch, sig[0], TOP_PAD_Y if up else BOT_PAD_Y, ch))
    if fault == "pad_swap":                                                     # 對照表寫錯：M1 兩個接墊名稱互換
        i = next(n for n, q in enumerate(pads) if q[0] == "M1_phi")
        j = next(n for n, q in enumerate(pads) if q[0] == "M1_theta")
        pads[i], pads[j] = (pads[j][0],) + pads[i][1:], (pads[i][0],) + pads[j][1:]
    buses = {}
    for net, yb, s in (("GND_T", TOP_BUS_Y, 1), ("GND_B", BOT_BUS_Y, -1)):
        xs = [l[0] for l in lines if l[3] == net]
        x0, x1 = min(xs) - W_LINE / 2, max(xs) + W_LINE / 2
        buses[net] = (x0, x1, yb)
        pads.append((net, BL.r3((x0 + x1) / 2), yb + s * PAD / 2, net))      # 接墊一半壓在匯流排上，向晶片外側
    return dict(lines=lines, pads=pads, buses=buses, side=side)


class Chip(i3.PCell):
    """整顆晶片：核心＋EC＋扇入／扇出＋金屬。fault：none／open／short／pad_swap／unmatched（扇入不等長）。"""
    core = i3.ChildCellProperty()
    contacts = i3.DictProperty()
    ops = i3.ListProperty()
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)
    ec_t = i3.NumberProperty(default=1.0)
    fault = i3.StringProperty(default="none")

    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            c = self.cell
            insts += i3.SRef(c.core, position=(0.0, 0.0), name="core")
            ec = EdgeCoupler(t=c.ec_t, n_eff=c.n_eff, n_g=c.n_g, name=f"EC_THIN_SI_{c.ec_t:.4f}")
            for k in range(5):
                insts += i3.SRef(ec, position=(X_LEFT, ec_y(k)), name=f"ECi{k}")
                insts += i3.SRef(ec, position=(X_RIGHT, ec_y(k)), transformation=i3.Rotation(rotation=180.0), name=f"ECo{k}")
                insts += i3.SRef(BL.wg(fanin_points(k, matched=c.fault != "unmatched"), c.n_eff, c.n_g), name=f"Fi{k}")
                insts += i3.SRef(BL.wg(fanout_points(k), c.n_eff, c.n_g), name=f"Fo{k}")
            return insts

        def _generate_elements(self, elems):
            c = self.cell
            pl = plan(c.ops, c.contacts, c.fault)
            for x, y0, y1, _ in pl["lines"]:
                elems += BL.rect(pdk.L_PAD, x - W_LINE / 2, min(y0, y1), x + W_LINE / 2, max(y0, y1))
            for net, (x0, x1, yb) in pl["buses"].items():
                elems += BL.rect(pdk.L_PAD, x0, yb - BUS_W / 2, x1, yb + BUS_W / 2)
            for name, x, y, net in pl["pads"]:
                elems += BL.rect(pdk.L_PAD, x - PAD / 2, y - PAD / 2, x + PAD / 2, y + PAD / 2)
                ty = y + PAD / 2 + 6 if y > 0 else y - PAD / 2 - 16
                elems += i3.PolygonText(layer=pdk.L_LABEL, text=name, coordinate=(x, ty), height=8.0)
            for k in range(5):
                elems += i3.PolygonText(layer=pdk.L_LABEL, text=f"IN{k}", coordinate=(X_LEFT + 120, ec_y(k) + 40), height=10.0)
                elems += i3.PolygonText(layer=pdk.L_LABEL, text=f"OUT{k}", coordinate=(X_RIGHT - 120, ec_y(k) + 40), height=10.0)
            elems += i3.PolygonText(layer=pdk.L_LABEL, text="B7_LOGIC_PIC", coordinate=(900.0, Y_DIE[0] + 40), height=20.0)
            elems += BL.rect(pdk.L_OUTLINE, X_LEFT, Y_DIE[0], X_RIGHT, Y_DIE[1])
            return elems

        def _generate_ports(self, ports):
            tt = pdk.wg_template()
            for k in range(5):
                ports += i3.OpticalPort(name=f"fiber_in{k}", position=(X_LEFT, ec_y(k)), angle=180.0, trace_template=tt)
                ports += i3.OpticalPort(name=f"fiber_out{k}", position=(X_RIGHT, ec_y(k)), angle=0.0, trace_template=tt)
            return ports

    class Netlist(i3.NetlistFromLayout):
        pass

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return i3.HierarchicalModel.from_netlistview(self.netlist_view)


def input_lengths(matched=True):
    """每條輸入在核心之前的光路長（µm）：EC ＋ 扇入（EC 以幾何長度計）。"""
    return np.array([EC_LEN + BL.poly_len(fanin_points(k, matched)) for k in range(5)])
