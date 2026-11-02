# B7 光邏輯 PIC：設計交付包

一顆 4 位元可程式光邏輯晶片：7 顆 MZI 組成 5 入 5 出的 B7，換 14 個 heater 相位就換邏輯功能（AND2、OR2、XOR2、AND4、OR4），
讀取 o2 與 o4 的功率差判定 0／1。製程：CORNERSTONE 220 nm SOI 被動平台（含 TiN heater）。

## 先看這三個
| 檔案 | 內容 |
|---|---|
| `layout/B7_final.gds` | 晶片版圖，3876 × 1200 µm；頂層 cell `B7_CHIP`。SHA-256 `5fc163e51a18717d73994170299e4b4644bc82cb4209a277de3f960dcdfe73e8` |
| `interfaces/optical_ports.csv` | 10 個邊緣耦合器端面座標；輸入 x1–x4、R，輸出 o1–o5（o2、o4 讀取） |
| `interfaces/pad_map.csv` | 16 個 80 × 80 µm 接墊：14 路 heater 訊號（通道名 M1_phi … M7_theta）與 GND_T、GND_B |

## 檢查結果（都針對上面的 SHA-256）
- DRC（CORNERSTONE pre-DRC 規則檔）：0 違規、外框外 0（通過）
- DRC 規則本身會觸發：12/12 條＋設計區（通過）
- 光學 LVS（只讀 GDS）：7 MZI、9 連線、10 外部埠、14 heater 與規格一致（通過）
- 電氣連接（只讀 GDS）：14 通道各接 1 訊號接墊＋回流；16 個金屬網（通過）
- 核心與已審查版本相同：逐多邊形相同（通過）
- 核心審查 8 項：全部通過（通過）
- 晶片電路 80 筆（1530–1570 nm）：80/80，不需重新校正（通過）
- 核心佈局抽連接表：與規格一致（通過）

範圍：pre-DRC：規則檔註明完整 DRC 由 CORNERSTONE 執行；LVS 只比對拓樸與 heater 位置，不含 EC 模態與損耗。

## 自己驗證
1. `python check_delivery.py`：逐檔比對 SHA-256（只需 Python）。
2. `python verify_gds.py`：只讀 GDS 重做光學 LVS 與電氣連接（需 numpy、shapely、matplotlib）。
3. `python rebuild_gds.py`：用 `source/` 的程式重建 GDS，逐多邊形比對（需 IPKISS 2026.3.3 與 CORNERSTONE 2.6.luceda1 授權）。
4. DRC：規則檔是 CORNERSTONE 的平台檔案，不隨本包散布；取得後用 KLayout（本包以 0.30.12 檢查）載入
   `layout/B7_final.gds`，設計區 3876 × 1200 µm，可對照 `reports/B7_final_drc.lyrdb`。

## 資料夾
| 資料夾 | 內容 |
|---|---|
| `layout/` | 晶片版圖；`B7_core_reviewed.gds` 是已審查的核心（晶片內的核心與它逐多邊形相同） |
| `reports/` | DRC 摘要與原始報告、連接檢查、簽核表、核心審查、晶片電路模擬 |
| `interfaces/` | 功能規格、連接表、I/O 表、外部設備需求、真值表、光學埠表、接墊表、佈局資訊 |
| `simulation/` | 相位設定（θ、φ，單位 rad）、PDK 電路的 U 矩陣與 80 筆結果 |
| `figures/` | 晶片全圖、接墊與金屬網、核心、LVS 抽出圖 |
| `source/` | 產生與檢查本版圖的程式（保留原資料夾結構） |

## 交接時要知道的事
- 相位設定是理想模型的數值；實體晶片要先量 heater 的「電壓 → 相位」再換算。加熱絲為 111.11 個方塊，電阻 = 111.11 × TiN 片電阻。
- 兩個 GND 接墊量測時接同一個地。
- 輸入的資料光與參考光必須同一雷射、相位穩定；外部設備的精度要求見 `interfaces/external_requirements.json`。
- 晶片內 5 條輸入光路等長；雷射波長在 1530–1570 nm 內不需重新校正 heater（模擬）。
- 邊緣耦合器是以 PDK 圖層自建的薄矽尖端，耦合效率未模擬；0.25 µm 尖端需向 CORNERSTONE 確認可製作。
- 金屬跨過直波導 24 處、熱串擾、EC 與傳播損耗均未建模，需量測。
- DRC 為 pre-DRC，完整 DRC 由 CORNERSTONE 執行。

## 工具版本
Python 3.14.3、IPKISS 2026.3.3、CORNERSTONE 2.6.luceda1、numpy 2.3.5、shapely 2.1.2、matplotlib 3.10.8、KLayout 0.30.12。
