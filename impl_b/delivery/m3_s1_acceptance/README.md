M3 S1：兩輪乾淨來源重建驗收。
入口 scripts/run_m3_s1.ps1；核心 scripts/rebuild_all.py。
清單 26 項均通過；原始 GDS SHA 不同，44 筆日期 payload 統一後 SHA 相同，全圖層 XOR／文字一致。
每輪 400 筆功能比較與 S7 差為 0。兩輪 24 項模型測試、10 項輔助測試、4 種控制通過。
完整結果 work/m3_s1/out/rebuild_results.json；新 GDS 與表格在 out/build_A 及 out/build_B。
預先安裝的授權工具與 M1 設計輸入為前提；不是 FEM/FDTD 重解、工具重新安裝或製程／實體功能簽核。
學員作答與講師驗收待完成。下一步 M3 S2。
