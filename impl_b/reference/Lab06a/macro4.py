"""新的 4-bit Macro（M2 s2b 全域最佳化定案）：5 條波導、7 顆 MZI 的磚牆排列，判讀 o2、o4，R 接第 5 條波導（邊緣）。

用途：全計畫共用的單級判讀 Macro 定義（取代 M1 的 Macro-18）。來源：M2 s2b 的 4 輸入窮舉——路徑指標篩選後的 56 個可控候選
（7、8、9 顆 MZI × 判讀輸出 × R 埠）全部以 222 個 NPN 類評估（global4_all.py，審查 R1）：本排列與判讀 o2、o4 是最佳者的基礎，
8、9 顆的最佳者只是本排列再加 MZI；同一排列 R 在第 3 條（中間）最好（≥0.1 P_u 141 類、對 T10 ×1.089），
本定案 R 在第 5 條為 138 類、×1.053（約低 3.4%），為佈局理由保留（使用者 2026-10-25 決定）。
排程：各層位置 [0, 3]、[1]、[0, 2]、[1, 3]（MZI 作用在模 p、p+1）；資料 x1–x4 依序接模 0–3。
R 位置：初選只比較 R 在第 4、5 條（兩者等效：222 類逐類比值中位數 1.000）；全部候選評估後 R 在第 3 條最好（見上）；
定案放第 5 條，佈局上 R 不必穿過資料線、資料輸入連續（2026-10-25）。R_PORT_OLD／DATA_PORTS_OLD 保留給定案前算出的結果重現。
輸入：無。
輸出：純定義（OPS、READOUT、R_PORT、DATA_PORTS、design()、mesh()、ports()），無檔案。
"""
from . import bigmesh as B

N = 5
OPS = [(0, 0), (3, 0), (1, 1), (0, 2), (2, 2), (1, 3), (3, 3)]     # (位置 p, 層)
READOUT = (1, 3)                                                     # o2、o4
R_PORT = 4                                                           # 第 5 條（邊緣）
DATA_PORTS = (0, 1, 2, 3)                                            # x1–x4
R_PORT_OLD, DATA_PORTS_OLD = 3, (0, 1, 2, 4)                         # 定案前（R 在第 4 條）


def design(name="Macro-B7", r_port=R_PORT, data_ports=DATA_PORTS):
    return B.Design(name, N, list(OPS), readout=READOUT, r_port=r_port, data_ports=data_ports)


def mesh():
    return design().mesh


def ports(srcs, r_port=R_PORT, data_ports=DATA_PORTS):
    """4 個資料來源 → 5 個埠的來源清單（R 在 r_port）。"""
    out = [None] * N
    out[r_port] = ("R",)
    for m, sc in zip(data_ports, srcs):
        out[m] = sc
    return out
