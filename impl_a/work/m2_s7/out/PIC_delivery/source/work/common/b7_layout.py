"""B7 核心佈局（M2 s3 起使用）：PDK MMI＋S 彎＋相位段組成 MZI，依規格 OPS 放成四欄五軌的 B7。

用途：產生可寫 GDS 的 IPKISS cell；每個 cell 的連接表由佈局抽出（i3.NetlistFromLayout，埠座標重合才算接上），
      電路模型由抽出的連接表組成（i3.HierarchicalModel），所以「佈局 → 連接 → S 矩陣」是同一份資料。
輸入：規格的 OPS、θ[7]、φ[7]；波導模板（填 femwell 的 n_eff、n_g）。
輸出：無檔案；MZI、B7Core cell，geometry() 回傳每段波導的長度表（供校正與報告）。

座標：rail r 的 y = −PITCH·r（rail 0 在最上面）；第 c 欄從 x = c·L_COL 開始；輸入引線從 x = −LEAD 起。
幾何沿用 M0 s1 已通過 DRC 的 MZI：相位段 122 µm、餘弦 S 彎 20 µm（最小半徑 5.23 µm）、TiN 0.9×100 µm。
等長旁路（matched）：沒有 MZI 的 rail 也走同樣的 S 彎與直線，讓每一欄每條 rail 的幾何長度相同。
"""
import math

import ipkiss3.all as i3
import numpy as np

import pdk

PITCH = 30.0            # rail 間距＝MZI 兩臂間距
SB_L, SB_STUB = 20.0, 0.5
HT_W, HT_L = 0.9, 100.0
LAND_W, LAND_M = 10.0, 1.0
PS_LEN = HT_L + 2 * (LAND_W + LAND_M)      # 122
LEAD = 60.0             # 輸入／輸出引線（M2 s5 接邊緣耦合器）

_MMI = pdk.mmi2x2()
_MP = {p.name: (p.position.x, p.position.y) for p in _MMI.Layout().ports}
M_IN, M_OUT, M_PY = _MP["in2"][0], _MP["out2"][0], _MP["in2"][1]
M_LEN = M_OUT - M_IN                        # 82.5（含錐形段，埠到埠）
DY = PITCH / 2 - M_PY                       # S 彎的橫移 13.985
L_COL = 2 * PS_LEN + 4 * SB_L + 2 * M_LEN   # 一欄長 489


def r3(v):
    return round(float(v), 3)


def sbend(x0, y0, y1, n=41):
    """餘弦 S 彎（與 M0 s1 相同），兩端各 SB_STUB 水平段，座標對齊 1 nm。"""
    u = np.linspace(0, 1, n)
    lc = SB_L - 2 * SB_STUB
    pts = [(x0, y0)] + [(x0 + SB_STUB + lc * t, y0 + (y1 - y0) * (1 - math.cos(math.pi * t)) / 2) for t in u] + [(x0 + SB_L, y1)]
    return [(r3(x), r3(y)) for x, y in pts]


def bump(x0, y0, length, extra, sign=1.0, n=81):
    """直線段上的升餘弦凸起，使路徑比直線多 extra µm（故障注入用）；回傳 (點列, 實際多出的長度)。"""
    def pts(h):                                  # 兩端各留 1 µm 水平段，埠的方向才會是正 0°／180°
        u = np.linspace(0, 1, n)
        lb = length - 2.0
        return ([(r3(x0), r3(y0))] + [(r3(x0 + 1.0 + lb * t), r3(y0 + sign * h * (1 - math.cos(2 * math.pi * t)) / 2))
                                      for t in u] + [(r3(x0 + length), r3(y0))])
    lo, hi = 0.0, 20.0
    for _ in range(60):
        h = (lo + hi) / 2
        lo, hi = (h, hi) if poly_len(pts(h)) - length < extra else (lo, h)
    p = pts(h)
    return p, poly_len(p) - length


def poly_len(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def join(*paths):
    out = []
    for p in paths:
        for q in p:
            if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
                out.append(q)
    return out


def rect(layer, x0, y0, x1, y1):
    return i3.Rectangle(layer=layer, center=(r3((x0 + x1) / 2), r3((y0 + y1) / 2)),
                        box_size=(r3(abs(x1 - x0)), r3(abs(y1 - y0))))


_TEMPLATES, _WGS = {}, {}


def make_template(n_eff, n_g, wl0=1.55):
    """strip 波導模板：佈局用 PDK 的核心寬，電路模型填 femwell 的 n_eff、n_g（PDK 預設 1.0／2.0 不是實際值）。"""
    key = (round(n_eff, 6), round(n_g, 6))
    if key not in _TEMPLATES:
        t = pdk.pdk.StripWaveguideTemplate()
        t.Layout(core_width=pdk.WG_W)
        t.CircuitModel(n_eff=n_eff, n_g=n_g, center_wavelength=wl0, loss_dB_m=0.0)
        _TEMPLATES[key] = t
    return _TEMPLATES[key]


def wg(pts, n_eff, n_g):
    """依形狀快取波導 cell（同形狀、同模板共用一個 cell，名稱依序編號）。"""
    key = (round(n_eff, 6), round(n_g, 6), tuple(pts))
    if key not in _WGS:
        w = i3.Waveguide(trace_template=make_template(n_eff, n_g), name=f"WG{len(_WGS):04d}")
        w.Layout(shape=list(pts))
        _WGS[key] = w
    return _WGS[key]


def beta(wl, n_eff, n_g, wl0=1.55):
    """與 Caphe 波導模型相同的一階色散：n(λ) = n_eff + (n_eff − n_g)(λ − λ0)/λ0，β = 2π n(λ)/λ（rad/µm）。"""
    wl = np.asarray(wl, dtype=float)
    return 2 * np.pi * (n_eff + (n_eff - n_g) * (wl - wl0) / wl0) / wl



class DelayModel(i3.CompactModel):
    """MMI 的電路替身：PDK 的理想 50:50（上埠 in2／out2 為直通），再乘上與 strip 等長的傳播相位。"""
    parameters = ["length", "n_eff", "n_g", "wl0"]
    terms = [i3.OpticalTerm(name=n) for n in ("in1", "in2", "out1", "out2")]

    def calculate_smatrix(parameters, env, S):
        wl = env.wavelength
        n = parameters.n_eff + (parameters.n_eff - parameters.n_g) * (wl - parameters.wl0) / parameters.wl0
        d = np.exp(1j * 2 * np.pi * n * parameters.length / wl) / np.sqrt(2)
        c = 1j * d                                  # Caphe 以 numba 編譯，只能逐一指定
        S["in1", "out1"] = d
        S["out1", "in1"] = d
        S["in2", "out2"] = d
        S["out2", "in2"] = d
        S["in1", "out2"] = c
        S["out2", "in1"] = c
        S["in2", "out1"] = c
        S["out1", "in2"] = c


class MMI(i3.PCell):
    """PDK 2×2 MMI 的包裝：佈局就是 PDK cell；電路模型加上埠到埠的等效傳播相位（假設，見頁面限制）。"""
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)

    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            insts += i3.SRef(reference=_MMI, name="pdk")
            return insts

        def _generate_ports(self, ports):
            for p in _MMI.Layout().ports:
                ports += i3.OpticalPort(name=p.name, position=p.position, angle=p.angle, trace_template=p.trace_template)
            return ports

    class Netlist(i3.NetlistView):
        def _generate_terms(self, terms):
            for n in ("in1", "in2", "out1", "out2"):
                terms += i3.OpticalTerm(name=n)
            return terms

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return DelayModel(length=M_LEN, n_eff=self.cell.n_eff, n_g=self.cell.n_g, wl0=1.55)


class PhaseModel(i3.CompactModel):
    """相位段：直波導傳播相位＋heater 設定的相位 e^{i·phase}。"""
    parameters = ["length", "n_eff", "n_g", "wl0", "phase"]
    terms = [i3.OpticalTerm(name="in"), i3.OpticalTerm(name="out")]

    def calculate_smatrix(parameters, env, S):
        wl = env.wavelength
        n = parameters.n_eff + (parameters.n_eff - parameters.n_g) * (wl - parameters.wl0) / parameters.wl0
        t = np.exp(1j * (2 * np.pi * n * parameters.length / wl + parameters.phase))
        S["in", "out"] = t
        S["out", "in"] = t


class PhaseSection(i3.PCell):
    """上臂的相位段：PS_LEN 直波導＋TiN heater（兩端 TiN 落墊、Ti/AL 接觸墊，無 via）。接墊扇出在 M2 s5。"""
    phase = i3.NumberProperty(default=0.0)
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)
    channel = i3.StringProperty(default="M1_phi")

    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            insts += i3.SRef(wg([(0.0, 0.0), (PS_LEN, 0.0)], self.cell.n_eff, self.cell.n_g), name="wg")
            return insts

        def _generate_elements(self, elems):
            x0, x1 = LAND_W + LAND_M, LAND_W + LAND_M + HT_L
            elems += rect(pdk.L_HT, x0 - LAND_W, -HT_W / 2, x1 + LAND_W, HT_W / 2)
            for xe, s in ((x0, -1), (x1, +1)):
                elems += rect(pdk.L_HT, xe, -LAND_W / 2, xe + s * LAND_W, LAND_W / 2)
                elems += rect(pdk.L_PAD, xe, -LAND_W / 2 - LAND_M, xe + s * (LAND_W + LAND_M), LAND_W / 2 + LAND_M)
            return elems

        def _generate_ports(self, ports):
            ports += i3.OpticalPort(name="in", position=(0.0, 0.0), angle=180.0, trace_template=pdk.wg_template())
            ports += i3.OpticalPort(name="out", position=(PS_LEN, 0.0), angle=0.0, trace_template=pdk.wg_template())
            return ports

    class Netlist(i3.NetlistView):
        def _generate_terms(self, terms):
            terms += i3.OpticalTerm(name="in")
            terms += i3.OpticalTerm(name="out")
            return terms

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return PhaseModel(length=PS_LEN, n_eff=self.cell.n_eff, n_g=self.cell.n_g, wl0=1.55, phase=self.cell.phase)


def mzi_segments(extra_lower_theta=0.0):
    """單顆 MZI 的波導形狀（局部座標：上臂 y = 0、下臂 y = −PITCH）。回傳 {名稱: 點列} 與各段長度。"""
    yu, yl, yc = 0.0, -PITCH, -PITCH / 2
    x = PS_LEN
    seg = {"lo_phi": [(0.0, yl), (PS_LEN, yl)]}
    seg["up_sb1"], seg["lo_sb1"] = sbend(x, yu, yc + M_PY), sbend(x, yl, yc - M_PY)
    x += SB_L + M_LEN
    seg["up_sb2"], seg["lo_sb2"] = sbend(x, yc + M_PY, yu), sbend(x, yc - M_PY, yl)
    x += SB_L
    if extra_lower_theta > 0:
        seg["lo_theta"], _ = bump(x, yl, PS_LEN, extra_lower_theta, sign=1.0)
    else:
        seg["lo_theta"] = [(x, yl), (x + PS_LEN, yl)]
    x += PS_LEN
    seg["up_sb3"], seg["lo_sb3"] = sbend(x, yu, yc + M_PY), sbend(x, yl, yc - M_PY)
    x += SB_L + M_LEN
    seg["up_sb4"], seg["lo_sb4"] = sbend(x, yc + M_PY, yu), sbend(x, yc - M_PY, yl)
    return seg


class MZI(i3.PCell):
    """一顆 MZI：φ 段 → S 彎 → MMI1 → S 彎 → θ 段 → S 彎 → MMI2 → S 彎；相位段在上臂（rail p）。
    埠 in0／out0 在上臂（rail p），in1／out1 在下臂（rail p+1）。flip=True 為故障注入（整顆上下翻轉）。"""
    theta = i3.NumberProperty(default=0.0)
    phi = i3.NumberProperty(default=0.0)
    k = i3.IntProperty(default=1)
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)
    extra_lower_theta = i3.NumberProperty(default=0.0)

    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            c = self.cell
            ne, ng = c.n_eff, c.n_g
            seg = mzi_segments(c.extra_lower_theta)
            yc = -PITCH / 2
            tag = "" if (c.theta == 0 and c.phi == 0) else f"_{c.theta:.6f}_{c.phi:.6f}"     # 相位 0 的版本寫 GDS
            insts += i3.SRef(PhaseSection(phase=c.phi, n_eff=ne, n_g=ng, channel=f"M{c.k}_phi",
                                          name=f"PS_M{c.k}_phi{tag}"), position=(0.0, 0.0), name="phi")
            xt = PS_LEN + 2 * SB_L + M_LEN
            insts += i3.SRef(PhaseSection(phase=c.theta, n_eff=ne, n_g=ng, channel=f"M{c.k}_theta",
                                          name=f"PS_M{c.k}_theta{tag}"), position=(xt, 0.0), name="theta")
            mmi = MMI(n_eff=ne, n_g=ng, name=f"MMI_{ne:.4f}_{ng:.4f}")
            insts += i3.SRef(mmi, position=(PS_LEN + SB_L - M_IN, yc), name="mmi1")
            insts += i3.SRef(mmi, position=(xt + PS_LEN + SB_L - M_IN, yc), name="mmi2")
            for n, pts in seg.items():
                insts += i3.SRef(wg(pts, ne, ng), name=n)
            return insts

        def _generate_elements(self, elems):
            x = PS_LEN + 2 * SB_L + M_LEN + PS_LEN / 2
            elems += i3.PolygonText(layer=pdk.L_LABEL, text=f"M{self.cell.k}", coordinate=(x, -PITCH / 2), height=8.0)
            return elems

        def _generate_ports(self, ports):
            tt = pdk.wg_template()
            ports += i3.OpticalPort(name="in0", position=(0.0, 0.0), angle=180.0, trace_template=tt)
            ports += i3.OpticalPort(name="in1", position=(0.0, -PITCH), angle=180.0, trace_template=tt)
            ports += i3.OpticalPort(name="out0", position=(L_COL, 0.0), angle=0.0, trace_template=tt)
            ports += i3.OpticalPort(name="out1", position=(L_COL, -PITCH), angle=0.0, trace_template=tt)
            return ports

    class Netlist(i3.NetlistFromLayout):
        pass

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return i3.HierarchicalModel.from_netlistview(self.netlist_view)


def bypass_points(x0, y0, matched=True):
    """沒有 MZI 的 rail 在一欄內的路徑。matched：與 MZI 臂相同的 S 彎與直線（往下橫移 DY）；否則一條直線。"""
    if not matched:
        return [(r3(x0), r3(y0)), (r3(x0 + L_COL), r3(y0))]
    x, pts = x0, [(r3(x0), r3(y0))]
    for _ in range(2):
        x += PS_LEN
        pts = join(pts, [(r3(x), r3(y0))], sbend(x, y0, y0 - DY))
        x += SB_L + M_LEN
        pts = join(pts, [(r3(x), r3(y0 - DY))], sbend(x, y0 - DY, y0))
        x += SB_L
    return pts


class B7Core(i3.PCell):
    """B7 核心：OPS 決定欄與 rail；空位補旁路；兩側引線；10 個外部埠 in0–in4、out0–out4。
    fault（故障注入）：None、"offset"（M5 右移 0.1 µm）、"wrong_rail"（M3 放到 rail 2–3）、
    "flip"（M6 上下翻轉）、"straight"（旁路改直線，不等長）、"arm"（M7 下臂 θ 段多 2 µm）。"""
    ops = i3.ListProperty()
    theta = i3.ListProperty()
    phi = i3.ListProperty()
    n_eff = i3.NumberProperty(default=2.35)
    n_g = i3.NumberProperty(default=4.15)
    fault = i3.StringProperty(default="none")

    class Layout(i3.LayoutView):
        def _generate_instances(self, insts):
            c = self.cell
            ne, ng = c.n_eff, c.n_g
            n_rail = 5
            busy = {}
            for k, (p, layer) in enumerate(c.ops):
                p_place = p + 1 if (c.fault == "wrong_rail" and k == 2) else p
                x = layer * L_COL + (0.1 if (c.fault == "offset" and k == 4) else 0.0)
                extra = 2.0 if (c.fault == "arm" and k == 6) else 0.0
                tag = "" if (c.theta[k] == 0 and c.phi[k] == 0) else f"_{c.theta[k]:.6f}_{c.phi[k]:.6f}"
                m = MZI(theta=c.theta[k], phi=c.phi[k], k=k + 1, n_eff=ne, n_g=ng, extra_lower_theta=extra,
                        name=f"MZI_M{k + 1}{tag}{'_arm' if extra else ''}")
                if c.fault == "flip" and k == 5:
                    insts += i3.SRef(m, position=(x, -PITCH * (p_place + 1)), transformation=i3.VMirror(), name=f"M{k + 1}")
                else:
                    insts += i3.SRef(m, position=(x, -PITCH * p_place), name=f"M{k + 1}")
                busy.setdefault(layer, set()).update({p, p + 1})
            for layer in range(4):
                for r in range(n_rail):
                    if r not in busy.get(layer, set()):
                        pts = bypass_points(layer * L_COL, -PITCH * r, matched=(c.fault != "straight"))
                        insts += i3.SRef(wg(pts, ne, ng), name=f"B{layer + 1}r{r}")
            for r in range(n_rail):
                insts += i3.SRef(wg([(-LEAD, -PITCH * r), (0.0, -PITCH * r)], ne, ng), name=f"Li{r}")
                insts += i3.SRef(wg([(4 * L_COL, -PITCH * r), (4 * L_COL + LEAD, -PITCH * r)], ne, ng), name=f"Lo{r}")
            return insts

        def _generate_elements(self, elems):
            elems += i3.PolygonText(layer=pdk.L_LABEL, text="B7_CORE", coordinate=(2 * L_COL, -4 * PITCH - 40.0),
                                    height=10.0)
            return elems

        def _generate_ports(self, ports):
            tt = pdk.wg_template()
            for r in range(5):
                ports += i3.OpticalPort(name=f"in{r}", position=(-LEAD, -PITCH * r), angle=180.0, trace_template=tt)
                ports += i3.OpticalPort(name=f"out{r}", position=(4 * L_COL + LEAD, -PITCH * r), angle=0.0,
                                        trace_template=tt)
            return ports

    class Netlist(i3.NetlistFromLayout):
        pass

    class CircuitModel(i3.CircuitModelView):
        def _generate_model(self):
            return i3.HierarchicalModel.from_netlistview(self.netlist_view)


def contract(nv, keep=lambda inst: inst.startswith("M")):
    """把抽出的連接表收斂成「MZI 埠 ↔ MZI 埠／外部埠」：沿兩端點的波導（旁路、引線）一路走到底。
    回傳 (links, external, dangling)：links 為 [src, dst]，external 為 {MZI 埠: 外部埠}，dangling 為沒接上的端點。"""
    adj = {}
    for key in nv.nets.keys():
        a, b = key.split("-")
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)

    def other(term):          # 兩端點元件的另一端
        inst, t = term.split(":")
        return f"{inst}:{'out' if t == 'in' else 'in'}"

    def walk(term):
        seen = 0
        while True:
            nxt = adj.get(term, [])
            if not nxt:
                return None
            t = nxt[0]
            if ":" not in t or keep(t.split(":")[0]):
                return t
            term = other(t)
            seen += 1
            if seen > 50:
                return None

    links, ext, dangling = [], {}, []
    for inst in nv.instances.keys():
        if not keep(inst):
            continue
        for t in ("out0", "out1"):
            d = walk(f"{inst}:{t}")
            if d is None:
                dangling.append(f"{inst}:{t}")
            elif ":" in d:
                links.append([f"{inst}:{t}", d])
            else:
                ext[f"{inst}:{t}"] = d
        for t in ("in0", "in1"):
            d = walk(f"{inst}:{t}")
            if d is None:
                dangling.append(f"{inst}:{t}")
            elif ":" not in d:
                ext[f"{inst}:{t}"] = d
    return links, ext, dangling


def geometry(matched=True):
    """每欄每條 rail 的幾何路徑長（µm）：MZI 的上臂、下臂與旁路；用於報告與「等長」檢查。"""
    seg = mzi_segments()
    up = PS_LEN * 2 + sum(poly_len(seg[f"up_sb{i}"]) for i in range(1, 5)) + 2 * M_LEN
    lo = sum(poly_len(seg[n]) for n in ("lo_phi", "lo_theta")) + sum(poly_len(seg[f"lo_sb{i}"]) for i in range(1, 5)) + 2 * M_LEN
    byp = poly_len(bypass_points(0.0, 0.0, matched))
    return dict(column_um=L_COL, mzi_upper_um=up, mzi_lower_um=lo, bypass_um=byp,
                sbend_um=poly_len(seg["up_sb1"]), dy_um=DY, mmi_len_um=M_LEN)


def segment_lengths(extra_lower_theta=0.0, matched=True):
    """校正用的各段長度（µm）：MZI 上下臂分成 前（φ 段＋S 彎）、中（S 彎＋θ 段＋S 彎）、後（S 彎），MMI 另計；旁路整段。"""
    s = mzi_segments(extra_lower_theta)
    L = {n: poly_len(p) for n, p in s.items()}
    return dict(pre_u=PS_LEN + L["up_sb1"], pre_l=L["lo_phi"] + L["lo_sb1"],
                mid_u=L["up_sb2"] + PS_LEN + L["up_sb3"], mid_l=L["lo_sb2"] + L["lo_theta"] + L["lo_sb3"],
                post_u=L["up_sb4"], post_l=L["lo_sb4"], mmi=M_LEN,
                bypass=poly_len(bypass_points(0.0, 0.0, matched)), lead=LEAD)


def calibrate(ops, theta, phi, wl, n_eff, n_g, extra=None, matched=True, input_um=None):
    """在波長 wl 把佈局的固定傳播相位吸收到 heater：φ' = φ − (兩輸入的相位差)、θ' = θ − (中段上下臂相位差)。
    依層序追蹤每條 rail 累積的相位；共同相位直接往後傳，最後只剩輸出端的相位（不影響功率）。
    extra：{MZI 編號 k（0 起）: 下臂 θ 段多出的長度}；input_um：核心之前每條 rail 的額外長度（例如晶片的扇入）。
    回傳 (θ'[7], φ'[7])，範圍 0–2π。"""
    b = float(beta(wl, n_eff, n_g))
    extra = extra or {}
    a = b * (LEAD + (np.zeros(5) if input_um is None else np.asarray(input_um, float)))
    th, ph = np.array(theta, float).copy(), np.array(phi, float).copy()
    for layer in range(4):
        busy = set()
        for k, (p, lay) in enumerate(ops):
            if lay != layer:
                continue
            g = segment_lengths(extra.get(k, 0.0), matched)
            ph[k] = (ph[k] - ((a[p] + b * g["pre_u"]) - (a[p + 1] + b * g["pre_l"]))) % (2 * np.pi)
            th[k] = (th[k] - b * (g["mid_u"] - g["mid_l"])) % (2 * np.pi)
            c = a[p + 1] + b * (g["pre_l"] + g["mid_l"] + 2 * g["mmi"])
            a[p], a[p + 1] = c + b * g["post_u"], c + b * g["post_l"]
            busy |= {p, p + 1}
        for r in range(5):
            if r not in busy:
                a[r] += b * segment_lengths(0.0, matched)["bypass"]
    return th, ph