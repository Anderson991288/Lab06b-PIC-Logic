# Lab06b C 槽課程

根目錄：C:\EDA_Codex\Lab06b；入口 Lab06b_index.html。
完整規劃：四模組、17 步，建議 18 小時。
M0 S1：scripts/run_m0_s1.ps1；工具鏈與正常／故障 MZI。
M0 S2：scripts/run_m0_s2.ps1；FEM、標量傳播與場圖分析；Meep FDTD 未重跑。
M0 S3：scripts/run_m0_s3.ps1；共用模型、單元測試與相容回放。
工具設定 EDA_paths.json；共用模型 work/common/mzi.py、linear_network.py。
M1 S1：scripts/run_m1_s1.ps1；光訊號編碼、參考光與功率判讀。
M1 S2：scripts/run_m1_s2.ps1；共用 B7、接線與 5×5 傳輸矩陣。
M1 S3：scripts/run_m1_s3.ps1；複數加權和、干涉分解與差分判讀。
M1 S4：scripts/run_m1_s4.ps1；五功能、80 筆真值及有號裕量。
M1 S5：scripts/run_m1_s5.ps1；pic_spec.json、phase_settings.json 與 delivery/m1_handoff.zip。
M2 S1：scripts/run_m2_s1.ps1；config/m2_boundary.json 與 delivery/m2_s1_io/。
M2 S2：scripts/run_m2_s2.ps1；work/m2_s2/out/comparison_80.csv（80/80，PDK 預設理想 MMI）。
M2 S3：scripts/run_m2_s3.ps1；work/m2_s3/out/b7_core.gds（初版 core，獨立回讀通過）。
M2 S4：scripts/run_m2_s4.ps1；採用版見 config/m2_current_core.json；修改前後見 work/m2_s4/out/。
M2 S5：scripts/run_m2_s5.ps1；晶片與對照表見 config/m2_current_chip.json。
M2 S6：scripts/run_m2_s6.ps1；全套現有 pre-DRC 與幾何網表比對、修正版見 config/m2_current_chip.json。
M2 S7：scripts/run_m2_s7.ps1；交付包 delivery/Lab06b_M2_PIC_delivery.zip，原設定線長回註 53/80，另存模型候選 80/80；實體資格未驗證。
M3 S1：scripts/run_m3_s1.ps1；兩輪乾淨來源重建、GDS 日期統一 SHA／全圖層 XOR／接口／400 筆比較通過。
M3 S2：scripts/run_m3_s2.ps1；獨立六項量測、54 判讀、八個 GDS 控制、12 測試通過，notch 差異與修正保留。
17 步教材與核心示範已建立；下一步：學員自主提交與講師整體驗收，實體／foundry 資格仍待完成。
原 C01 保留原位，更新備份放 history/。
