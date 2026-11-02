"""CORNERSTONE Si220 被動平台的 PDK 轉接層（M0 s2）。

用途：集中圖層、波導模板、標準元件與設計規則數值；換 foundry 或版本只改這裡。
輸入：IPKISS 3 的 cornerstone 技術庫（需授權）。
輸出：無檔案；提供 L_WG、L_HT、L_PAD、L_OUTLINE、L_LABEL、wg_template()、mmi2x2()、RULES。
"""
import cornerstone.all as pdk
from ipkiss.process.layer import PPLayer

WG_W = 0.45     # strip 核心寬（µm），與 PDK 2×2 MMI 的埠寬一致

L_WG = pdk.TECH.PPLAYER.WG                                          # GDS 3   Si 全蝕刻（strip 波導）
L_HT = pdk.TECH.PPLAYER.HT                                          # GDS 39  TiN heater
L_PAD = pdk.TECH.PPLAYER.PAD                                        # GDS 41  Ti/AL 電極與 pad（直接壓在 TiN 上，無 via）
L_OUTLINE = PPLayer(pdk.TECH.PROCESS.NONE, pdk.TECH.PURPOSE.CELL)   # GDS 99  設計區外框
L_LABEL = PPLayer(pdk.TECH.PROCESS.NONE, pdk.TECH.PURPOSE.LBL)      # GDS 100 文字

# MPW #50 被動平台規則（µm），與 DRC deck 的檢查一一對應；設計時引用，不在程式裡另寫數字
RULES = {
    "WG_min_width": 0.35, "WG_min_gap": 0.20,          # GDS 3
    "HT_min_width": 0.60, "HT_min_gap": 10.0,          # GDS 39
    "PAD_min_width": 2.0, "PAD_min_gap": 10.0,         # GDS 41
    "LBL_min_width": 0.25, "LBL_min_gap": 0.25,        # GDS 100
    "grid": 0.001,                                     # 製造格點 1 nm
    "bend_min_radius": 5.0,                            # PDK 標準 strip 彎道半徑
}

_TT = None


def wg_template():
    """strip 波導模板（核心寬 WG_W），所有波導共用同一個物件。"""
    global _TT
    if _TT is None:
        _TT = pdk.StripWaveguideTemplate()
        _TT.Layout(core_width=WG_W)
    return _TT


def mmi2x2():
    """PDK 標準 2×2 MMI（1550 nm TE strip）；埠位置由 Layout().ports 讀取，不寫死。"""
    return pdk.SOI220nm_1550nm_TE_STRIP_2x2_MMI()
