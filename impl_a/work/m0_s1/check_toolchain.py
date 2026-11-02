"""M0 s1 工具鏈檢查：路徑設定、IPKISS 授權、PDK、femwell、KLayout、Meep，以及 E1（MZI 佈局＋DRC）結果。

用法：
    C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m0_s1\\check_toolchain.py
輸出：out/toolchain_check.json；每一項 status 為 pass／fail／missing／blocked，並附 fix（下一步怎麼修）。
      實際路徑只寫在 JSON 的 path 欄位；detail 會放進課程頁面，所以只寫設定鍵名與工具輸出，不寫本機路徑。
本程式只讀取與試呼叫工具，不修改任何安裝。WSL 只呼叫 Ubuntu，不呼叫 EDA_Server。
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

CFG = json.loads(Path(r"C:\LAB\Lab06b\impl_a\EDA_paths.json").read_text(encoding="utf-8"))
W = {k: os.path.expandvars(v) for k, v in CFG["windows"].items()}
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    text = (p.stdout + p.stderr).decode("utf-8", errors="replace")
    return p.returncode, text.replace("\x00", "").strip()


def last_line(text):
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[-1].strip() if lines else ""


items = []


def add(id_, name, status, detail, fix="", path=None):
    items.append(dict(id=id_, name=name, status=status, detail=detail, fix=fix, path=path))
    print(f"[{status:7}] {id_} {name}: {detail}" + (f"  ({path})" if path else ""))


# 1. 路徑設定：EDA_paths.json 列出的每個位置都要存在（KLayout 另在 T5 檢查）
for key, label in (("ipkiss_python", "IPKISS Python"), ("conda", "conda"), ("device_sim_env", "device_sim 環境"),
                   ("pdk_cornerstone", "CORNERSTONE PDK"), ("drc_deck", "DRC deck")):
    ok = Path(W[key]).exists()
    add("P", f"路徑：{label}", "pass" if ok else "missing", f"windows.{key} " + ("存在" if ok else "找不到"),
        "" if ok else "修正 EDA_paths.json 的對應欄位", path=W[key])
course = Path(CFG["course"]["path"])
ok = (course / "work" / "common" / "runtime.py").exists()
add("P", "路徑：課程根目錄", "pass" if ok else "missing", "course.path 存在，含 work/common" if ok else "找不到",
    path=str(course))

# 2. IPKISS 授權（import ipcore 會先檢查授權）
code, txt = run([W["ipkiss_python"], "-c", "import ipkiss3.all as i3, ipkiss; print('IPKISS', ipkiss.__version__)"])
ipkiss_ok = code == 0
add("T1", "IPKISS 3 匯入與授權", "pass" if ipkiss_ok else "fail",
    last_line(txt) if ipkiss_ok else ("License error" if "License error" in txt else last_line(txt)),
    "" if ipkiss_ok else "以 Luceda Control Center 啟用授權，再重跑本檢查。")

# 3. CORNERSTONE PDK 實際載入：建立 2×2 MMI 並讀埠名
if ipkiss_ok:
    code, txt = run([W["ipkiss_python"], "-c",
                     "import cornerstone.all as pdk; m=pdk.SOI220nm_1550nm_TE_STRIP_2x2_MMI(); "
                     "print('MMI ports', [p.name for p in m.Layout().ports])"])
    add("T2", "CORNERSTONE PDK 載入（2×2 MMI）", "pass" if code == 0 else "fail", last_line(txt))
else:
    add("T2", "CORNERSTONE PDK 載入（2×2 MMI）", "blocked", "需先通過 T1（IPKISS 授權）")

# 4. device_sim（femwell）：必須經 conda run，直接執行 python.exe 會在 scipy LAPACK 無聲崩潰
code, txt = run([W["conda"], "run", "--no-capture-output", "-p", W["device_sim_env"], "python", "-c",
                 "import femwell, skfem, numpy, importlib.metadata as m; "
                 "print('femwell', m.version('femwell'), 'skfem', m.version('scikit-fem'), 'numpy', numpy.__version__)"])
t4 = "pass" if code == 0 else ("missing" if "No module named" in txt else "fail")
add("T4", "device_sim 環境（femwell）", t4, last_line(txt)[:160],
    {"pass": "", "fail": "檢查 conda run 的錯誤訊息與套件相依。",
     "missing": "conda run -p <device_sim> pip install femwell（numpy 釘住 1.26.4）"}[t4])

# 5. KLayout
kl = Path(W["klayout_exe"])
if kl.exists():
    code, txt = run([str(kl), "-b", "-v"])
    add("T5", "KLayout 批次模式", "pass" if code == 0 else "fail", last_line(txt))
else:
    add("T5", "KLayout 批次模式", "missing", "windows.klayout_exe 找不到", path=str(kl), fix=
        "安裝 KLayout（Windows 64-bit）到 %APPDATA%\\KLayout，使 klayout_app.exe 位於該資料夾。")

# 6. WSL Ubuntu：Meep（只用 Ubuntu；不呼叫 EDA_Server）
mp = CFG["wsl"]["meep"]
code, txt = run(["wsl", "-d", mp["distro"], "-u", mp["user"], "-e", "bash", "-c",
                 f"{mp['conda']} run -n {mp['env']} python -c 'import meep; print(\"meep\", meep.__version__)'"],
                timeout=180)
ok7 = code == 0 and "meep" in txt
add("T7", f"WSL {mp['distro']}（{mp['user']}）：Meep FDTD", "pass" if ok7 else "missing",
    next((l.strip() for l in txt.splitlines() if l.startswith("meep ")), last_line(txt)[:160]) or f"exit {code}",
    "" if ok7 else f"Ubuntu 建立使用者 {mp['user']}、安裝 Miniforge，conda create -n meep -c conda-forge pymeep")

# 7. E1：MZI 佈局＋DRC 故障注入（由 build_mzi_drc.py 產生）
e1 = OUT / "mzi_drc_result.json"
if not e1.exists():
    add("E1", "MZI 佈局＋DRC 故障注入", "blocked", "尚未執行 build_mzi_drc.py")
else:
    r = json.loads(e1.read_text(encoding="utf-8"))
    c, f = r["drc_clean"], r["drc_fault"]
    add("E1a", "MZI 正常版 GDS 與外框檢查", "pass" if c["outside"] == 0 else "fail",
        f"長 {r['mzi']['length']} µm；外框外圖形 {c['outside']}")
    add("E1b", "故障版 F6（外框外圖形）", "pass" if f["outside"] == 1 else "fail", f"外框外圖形 {f['outside']}（預期 1）")
    if c["status"] == "ran":
        add("E1c", "正常版 KLayout DRC", "pass" if c["total"] == 0 else "fail",
            f"{c['n_rules']} 條規則，違規 {c['total']}")
        add("E1d", "故障注入命中", "pass" if f["all_caught"] and not f["unexpected"] else "fail",
            f"各故障 {f['hit']}；意外的規則 {f['unexpected']}")
    else:
        add("E1c", "正常版 KLayout DRC", "blocked", c["reason"], "裝好 KLayout 後重跑 build_mzi_drc.py")
        add("E1d", "故障注入命中（F1–F5、F7、F8）", "blocked", f["reason"], "同上")

summary = {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "missing", "blocked")}
result = dict(step="M0 s1", time=datetime.datetime.now().isoformat(timespec="seconds"),
              python=sys.version.split()[0], summary=summary, items=items)
(OUT / "toolchain_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("summary", summary)
