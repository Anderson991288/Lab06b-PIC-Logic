# Lab06b Virtuoso／Calibre 本日完整重現

本次結果日期：2026-10-31。唯一正式工作區 C:\EDA_Codex\Lab06b；D 槽唯讀。
完整報告：Lab06b_index.html 的「實機重現」；分頁 course/virtuoso_calibre.html。

## 版本與範圍

WSL EDA_Server／AlmaLinux 8.10，Virtuoso IC23.1-64b.ISR15.37，Calibre 2026.1_17.11，KLayout 0.30.12。
本次使用供應商仍提供的 classic Interactive，以及實際 RVE。GUI_auto_saved.runset／GUI_fixed_saved.runset 是本次 GUI 實際儲存的 classic 格式；不要用舊 C01 新式 Qt Runset 代替。
本機必須已有可正常啟動的 CAD、授權與 DISPLAY。封裝不包含 CAD 軟體、授權檔或 qualified PDK。
OA 是 Stream-In 自動技術庫，Layout XL 因無 validLayers／validVias 停用抽取；不等於合格 foundry Virtuoso PDK。

## 原採用版與本次互通版

原 S6 採用 GDS：work/m2_s6/out/after/b7_ec_pad.gds，SHA-256 0a8bece1fddd9e10a5cac8369ac57259f5775735b4f5ef6758ab76ceddc23963。
原採用索引、規格、相位、M1／M2 ZIP 保留。本次最終檔另存為 work/virtuoso_reproduction/out/exports_final/B7_crosscad_final.gds。
只調整 GDS100 的 19 群註記，繞原中心放大 1.3；六個實體圖層 XOR0，16 個 GDS1002 文字不變。
43 個 cell 原名在 GDS 保留；C 槽 OA 明確轉小寫，43 筆無碰撞，輸出以 cell.map 還原。

## 從空白 OA 再重播

在 Windows PowerShell 執行；每次建立新目錄，不刪除／覆寫上一輪 OA：

```powershell
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' C:\EDA_Codex\Lab06b\work\virtuoso_reproduction\replay_prepare.py
wsl.exe -d EDA_Server -- bash /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/replay_native.sh
& 'C:\luceda\luceda_2026033\envs\device_sim\python.exe' C:\EDA_Codex\Lab06b\work\virtuoso_reproduction\verify_clean.py
```

本日已執行一次成功的完整空白 OA 重播。結果 out/clean_replay.json；逐檔證據 out/clean_replay/。
原始 OA 200／8191：原始 KLayout pre-DRC 8／0；200 的 GDS3 XOR25744 nm²，8191 XOR0。
註記修正版 8191：Calibre 草稿 0、原始 pre-DRC 0、15 金屬網／14 heater／33 光學連接通過。
原始版 Calibre 27 筆字形間距；故障控制每條規則各 1，共 16。草稿和原始 deck 沒有改動。
raw GDS 包含日期，重播以保留 raw SHA 加上實際 XOR／TEXT／cell 名與接線核對。

## 開啟實際 Virtuoso 畫面與 GUI 重播

現有本機 OA：C:\EDA_Codex\Lab06b\work\virtuoso_reproduction\work\oa_crosscad\lab06b_crosscad_20261031。
這是可重新產生的本機 CAD 資料庫；可攜包以 GDS、映射與來源重建它。

```powershell
wsl.exe -d EDA_Server -- bash /mnt/c/EDA_Codex/Lab06b/work/virtuoso_reproduction/open_review.sh
```

本機 OA 不存在時，先在 canonical C 專案執行 import_crosscad.sh（其原始 GDS 在 out/input/）。
開啟後為唯讀 Layout；Calibre 選單來自已安裝的 calibre.skl。

1. Calibre → Run nmDRC；本腳本設定 classic Interactive。Rules 選 out/rules/cornerstone_basic_draft.svrf。
2. File → Load Runset：out/GUI_auto_saved.runset。確認 Export from layout viewer 勾選，library=lab06b_crosscad_20261031、top=lab06b_b7_ec_pad_chip、view=layout。Run DRC；目錄 out/gui_auto。
3. 自動匯出的 Calibre 結果為 0，但同一 GDS 的原始 KLayout pre-DRC 有 8 筆。out/gui_auto/PIPO.LOG.* 與 xStrmOut_layerMap.txt 保留實際自動匯出記錄。
4. File → Load Runset：out/GUI_fixed_saved.runset。確認取消 Export from layout viewer，直接讀 out/exports_final/B7_crosscad_final.gds，top=LAB06B_B7_EC_PAD_CHIP；Run DRC → Summary → Start RVE。
5. 最終 RVE 16 個綠色檢查／0 results；同一檔案原始 pre-DRC 0。完整 transcript、drc.summary、drc.results 都在 out/gui_fixed。

GUI Runsets 是本次 canonical C 路徑；搬移包後需先在 GUI 改 Rules／Run directory／GDS path，再 Save Runset As。
原生截圖 out/screenshots/virtuoso_final.png、virtuoso_core.png、calibre_auto_inputs.png、calibre_fixed_inputs_0.png、rve_final.png；都是實際 Linux X11 視窗像素，未編修。

## 封裝內容與限制

本包含最終／原始／200 點／GUI 自動匯出 GDS、層／名稱映射、GUI Runset、16 項自寫草稿、正負例結果、完整 KLayout 報告、原生截圖、乾淨重播證據與來源腳本。
manifest.json 綁定每個檔案 SHA-256；外層 archive 的 SHA 位於 config/virtuoso_package.json。
專案保留已安裝 CORNERSTONE 原始 pre-DRC 的路徑／SHA；執行完整重播仍需完整 C 專案與對應本機工具。
16 項是有限 width／space 草稿，31 類是現有 pre-DRC。沒有宣稱 foundry 完整 DRC、qualified LVS、流片、製造完成或實測光電／熱功能。
