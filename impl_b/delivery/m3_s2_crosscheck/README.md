M3 S2 獨立幾何量測與交叉驗證
正式入口 scripts/run_m3_s2.ps1。
gdstk 1.0.2／Shapely 2.1.2 直接回讀同一 GDS，與 KLayout 六項寬度／間距比對；未使用 KLayout polygon export。
六項最小見證 µm：Si 0.350／0.530、HT 0.900／50.000、PAD 8.000／13.500；KLayout 1 nm 區間一致。
54 項判讀、8 個實際控制 GDS、12 項測試通過。原始全套 pre-DRC 31 類、0 筆。
保留 notch 初版 1.579456→修正 0.530000 µm 的差異與單側極限說明。
完整資料 work/m3_s2/out/；教材 course/m3_s2.html。
只有六項範圍內的 facing-edge 量測，不是全 deck 的獨立實作或 foundry／實體功能簽核。
17 步教材／核心示範已建立；學員自主交付與講師驗收仍待完成。
