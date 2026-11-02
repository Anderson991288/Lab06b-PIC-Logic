# Lab06b — 光運算邏輯 PIC 實作課程：從 MZI 邏輯到一顆可交付的 B7 光子晶片

Lab06b 是一套以 **CORNERSTONE Si220 被動製程 PDK** 為平台的矽光子（PIC）實作課程。學員在自己的工具鏈上，
依序做出一顆 **4-bit B7 光邏輯 PIC**：看懂 MZI 如何用光做 AND／OR／XOR → 用模型驗證 80 筆真值表 →
用 IPKISS 寫出佈局 → Review、配置 EC 光學 I/O 與 heater PAD → DRC 與連接檢查 → 交付可重現的設計資料包。

與原版課程的差別：原版是講師把既有結果整理成教材；本課程每一步都要學員**在自己的電腦重新執行**，
由程式產生證據 JSON，再由證據產生頁面。沒有重跑的內容一律標「引用」。

課程入口：[`Lab06b_index.html`](Lab06b_index.html)（總目錄）→ [`course/`](course/) 17 個步驟頁。

## 四個模組

| 模組 | 目標 | 關鍵能力 | 建議時數 | 狀態 |
|---|---|---|---|---|
| M0 環境與元件 | 工具鏈可執行；看懂 MMI／MZI 的光怎麼走 | 路徑設定與 DRC 故障注入、femwell 模態、Meep FDTD 光場、T(θ,φ) 模型 | 3.5 h | 通過 |
| M1 光訊號做邏輯 | 7 顆 MZI 組成 B7，換相位就換功能 | 5×5 矩陣 U、ΔP 判讀、80 筆真值表、相位誤差容忍度、規格交接 | 5 h | 通過 |
| M2 PIC 實作 | 從電路模型到可交付的晶片 GDS | IPKISS／Caphe 電路模擬、核心與晶片佈局、Layout Review、DRC、光學 LVS、交付包 | 8 h | 通過 |
| M3 驗收與延伸 | 別人能從零重做出同一顆晶片 | 一鍵重建、換一種方法做幾何檢查 | 1.5 h | 通過 |

每一步固定六段：**這一步要回答 → 白話範例 → 學員操作 → 檢查結果（由證據產生）→ 驗收條件 → 程式、檔案與歷史**。
主作業固定單顆 B7；原版的 B7×2 晶片只作講師參考。

## 晶片規格（主線）

| 指標 | 規格 | 備註 |
|---|---|---|
| 製程平台 | CORNERSTONE Si220 被動（PDK 2.6） | DRC 規則 30 條，用到的 12 條以故障注入確認會觸發 |
| 邏輯核心 | B7：7 顆 MZI、5 條波導、4 層、14 個相位通道 | 輸入 x1–x4 + 參考光 R；讀取 o2／o4 的 ΔP |
| 可程式功能 | AND2／OR2／XOR2／AND4／OR4 | 各 16 組，共 80 筆全對；最小裕量 XOR2 0.25 |
| 相位精度 | σ ≤ 0.02 rad 全對 | 相位檔與規格分開，以 SHA-256 綁定 |
| 波長範圍 | 1530–1570 nm 不需重新校正 | 旁路與 MZI 臂等長（510.133 µm） |
| 核心尺寸 | 2076 × 177 µm | DRC 0 違規 |
| 晶片尺寸 | 3876 × 1200 µm | 10 個薄矽尖端 EC、等長扇入（差 2×10⁻⁵ µm） |
| 電氣介面 | 14 個 heater 訊號網 + 2 個回流網，單層金屬 | 訊號在內、回流在外；無短路開路 |
| 交付包 | `B7_PIC_delivery.zip`，53 個檔案 | 解壓後只用包內程式重建出相同的 969 個多邊形 |

## 工具鏈

| 工具 | 版本 | 用途 |
|---|---|---|
| Luceda IPKISS 3 | 2026.03.3 | 佈局（Python）、Caphe 電路模擬、從佈局抽連接表 |
| CORNERSTONE PDK | 2.6（luceda1） | 2×2 MMI、層定義、DRC deck |
| femwell | 0.1.12 | 波導模態（TE0 n_eff） |
| Meep | 1.35.0（WSL Ubuntu） | 2D FDTD 光場傳播圖 |
| KLayout | 0.30.12 | 批次 DRC、GDS 檢視 |
| Cadence Virtuoso／Siemens Calibre | — | M2 s7 批次匯入匯出與 DRC 交叉比對（選用） |
| Python | NumPy、SciPy、Shapely、Matplotlib | 模型、獨立幾何檢查、繪圖 |

所有工具路徑統一由 [`impl_a/EDA_paths.json`](impl_a/EDA_paths.json) 讀取，頁面不出現本機路徑。
IPKISS 與 CORNERSTONE PDK 需自行取得授權，本 repo 不含這兩者。

## 兩套獨立實作，合併成一份課程

本課程由兩套各自獨立完成的實作合併而成（2026-11-01）。兩套都從同一份原始教材出發，各自寫程式、各自跑結果，不共用數字。

| 範圍 | 兩套的關係 |
|---|---|
| M0 s1 – M2 s2 | 模型、約定與 80 筆真值表一致，等於多了一次獨立驗證 |
| M2 s3 – M3 s2 | 兩套做出**不同的佈局**（旁路是否等長、S 彎長度、晶片尺寸、扇入、接地），數字不能混用，頁面上分開列 |

- **主線**：每一頁的正文、數字與驗收沿用實作 A（`impl_a/`）。
- **對照**：每一頁另有一節「對照：另一套獨立實作」，寫出實作 B（`impl_b/`）的做法與結果。
- **不互相改寫**：兩套程式各自保留原樣、各自可以重跑。

主線採用實作 A 的佈局，理由：旁路等長（不改相位就 80/80）、扇入等長、每一步都有 DRC 與抽出的電路、交付包能重建 GDS。
實作 B 的長處（更大的 S 彎半徑、交叉綁定測試、Virtuoso 視窗與 Calibre RVE 操作、真實 DRC 違規的修正流程）都放進各頁的對照一節。

## 驗收關卡

| 關卡 | 通過條件 |
|---|---|
| G0 工具鏈 | IPKISS／PDK 實際執行、正常 MZI DRC 0、F1–F8 故障命中、原始 log 留存 |
| G1 邏輯 | 固定 B7 光路、埠序與判讀；5 種功能各 16 組，共 80 組 |
| G2 版圖 | 模型和 GDS 共用埠名與相位標籤；EC、接墊、接地都有去向；旁路與扇入等長 |
| G3 幾何與連接 | 平台規則全部通過，且用到的規則以故障注入證明會觸發；光路連接、電氣開路短路另外驗證 |
| G4 交付 | 線長回填後功能重跑；GDS、相位、埠／接墊表、工具版本與 manifest 一致；解壓後能重建與重驗 |

## 目錄結構

| 路徑 | 內容 |
|---|---|
| `Lab06b_index.html` | 課程總目錄：規劃、進度、所有步驟入口 |
| `course/` | 17 步合併頁（單檔，圖已嵌入）；`course.css`；`figures/`（主線）、`figures_b/`（實作 B） |
| `impl_a/` | 主線（實作 A）的程式與證據：`EDA_paths.json`、`env/`、`sources/`、`spec/`、`work/<step>/out/` |
| `impl_a/work/common/` | 共用模型（`mzi.py`、`b7.py`、`runtime.py`）與 DRC deck |
| `impl_b/` | 實作 B 的程式與證據：`scripts/`、`work/`、`config/`、`evidence/`、`learner/`、`delivery/` |
| `merge/` | 合併工具與各頁的「對照」段落（`fragments/`） |
| `AGENT.md` | 工作規則 |

步驟代號 `m<模組>_s<步驟>`，例如 `m2_s5` = M2 第 5 步（晶片介面佈局）。

### 本 repo 未收錄的內容

| 內容 | 原因 | 如何取得 |
|---|---|---|
| `impl_b/tools/KLayout/` | 可攜版執行檔 684 MB | 自行安裝 KLayout 0.30.x |
| `*.npz`（Meep 光場） | 每檔 3–19 MB | `impl_a/work/m0_s2/run_fields.sh` 重算（約 4 h／案例）；圖已存成 PNG |
| 原版課程教材（`impl_b/reference/C01/`、`C01_original.zip`） | 非本課程原創 | — |
| `impl_b/history/`、重建副本、瀏覽器截圖 | 過程備份 | — |

## 重跑方式

| 實作 | 怎麼跑 |
|---|---|
| 主線（A） | 在 `impl_a/` 依各步「學員操作」執行；或用 `work/m3_s1/rebuild_all.py` 一次重建（約 7 分鐘，Meep 光場以 SHA-256 沿用） |
| 實作 B | 在 `impl_b/` 執行 `scripts/run_m*_s*.ps1`（每步一支） |

重新產生合併頁（IPKISS 的 Python 環境）：

```
python merge/build_course.py
python merge/build_index.py
```

`impl_a/work/<step>/build_page.py` 會更新 `impl_a/course/` 的主線頁；更新後要再跑上面兩行，合併頁才會跟著更新。

合併工具：

- `relocate.py`：把 `impl_a` 程式裡寫死的舊根目錄改成新位置（49 個程式與設定檔；log／證據保留原文）。
  `impl_b` 的程式都被它自己記錄的來源 SHA-256 釘住（835 個路徑），改一個字就會讓完整性檢查失敗，所以一律不改。
- `build_course.py`：主線頁 + `fragments/<step>.html` → `course/<step>.html`；自動順延節號、嵌入圖、檢查不含本機路徑。
- `build_index.py`：主線總目錄 + 合併說明、對照欄、關卡表、待解問題、重跑方式 → `Lab06b_index.html`。
- `peek_page.py`、`show_refs.py`：檢視頁面結構與節號引用。

搬到新位置後的確認（2026-11-01）：

- `impl_a`：從零重建 20 支程式，126 個輸出中 122 個相同或內容等價，4 個只差檔案內記錄的執行日期（`merge/rerun_impl_a.log`）。
- `impl_b`：`run_m1_s4.ps1`、`run_m2_s2.ps1`、`run_m3_s2.ps1` 都通過（`merge/rerun_impl_b.log`）。
  `scripts/rebuild_all.py`（M3 s1）內有原始根目錄檢查且其雜湊被記錄，在新位置不能直接重跑。

> 程式內仍有作者本機的絕對路徑（`C:\LAB\Lab06b\...`、`C:\luceda\...`）。在其他電腦重跑前，先改 `impl_a/EDA_paths.json`，再用 `merge/relocate.py` 改根目錄。

## 待確認事項

- **S 彎半徑**：主線最小曲率半徑 5.23 µm 通過 PDK DRC，但兩套都沒有彎道損耗的模擬或量測；實作 B 認為應拉大到 7.5 µm 以上。
- **實作 B 的 53/80**：線長回註後用原相位只有 53/80，可能來自直旁路的真實長度差，或回註模型沒有計入 MMI 本體長度。
- **模型**：PDK 電路模型是理想元件（MMI 無損 50:50，波導預設 n_eff＝1、n_g＝2）；MMI 相位用等長條狀波導等效。
- **沒有實體驗證**：沒有下線、封裝與量測；Virtuoso 沒有 CORNERSTONE 的製程套件；沒有 Calibre LVS。
- **學員作答**：各步的判讀練習與作答範本（`impl_b/learner/` 的 17 個 JSON）需要學員本人完成，由講師驗收。

## 版本歷程

| 版本 | 日期 | 重點變更 |
|---|---|---|
| v1 | 2026-10 | 實作 A：一步一頁、證據 JSON 產生頁面、補上 M0 |
| v2 | 2026-10-31 | 實作 A／B 各自完成 M0–M3；Virtuoso／Calibre 交叉比對 |
| v3 | 2026-11-01 | 兩套實作合併成一份課程，主線 + 對照 |
| v3.1 | 2026-11-02 | 上傳 GitHub：補 README、AGENT.md、`.gitignore` |
