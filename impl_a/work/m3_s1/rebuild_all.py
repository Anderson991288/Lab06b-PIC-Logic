"""M3 s1：一鍵從零重建。把課程程式複製到乾淨資料夾，依相依順序重跑整條流程（M0 s2 → M2 s7），再逐檔與現有結果比對。

用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\impl_a\\work\\m3_s1\\rebuild_all.py   （約 5–10 分鐘）
輸入：課程的 work/**/*.py、DRC 規則檔、EDA_paths.json；原始參考資料（唯讀，由 collect_* 程式讀取）；
      M0 s2 的 Meep 光場結果 field_*.json／.npz（每個 MZI 情況約 4 小時，不重跑，以 SHA-256 記錄後沿用）。
輸出：out/rebuild/（重建出的整個課程樹）、out/rebuild/logs/*.log、out/rebuild_report.json。
比對規則：GDS 比多邊形（檔頭含寫出時間）；JSON／CSV／文字先把重建資料夾路徑換回原路徑、把「已確認等價的檔案」的新雜湊換回舊雜湊，
         再逐值比對（數值相對誤差 ≤ 1e-9，執行時間欄位除外）；PNG 先比位元組、不同再比像素。重複直到沒有新的等價檔案。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "work" / "common"))
sys.stdout.reconfigure(encoding="utf-8")
import gds2png as G  # noqa: E402

CFG = json.loads((ROOT / "EDA_paths.json").read_text(encoding="utf-8"))["windows"]
PY = CFG["ipkiss_python"]
CONDA, DEVSIM = CFG["conda"], CFG["device_sim_env"]
DEST = HERE / "out" / "rebuild"
t0 = time.time()

# 依相依順序；(步驟, 程式, 執行環境)
STEPS = [
    ("M0 s2", "m0_s2/collect_reference.py", "ipk"), ("M0 s2", "m0_s2/waveguide_modes.py", "femwell"),
    ("M0 s2", "m0_s2/export_mmi.py", "ipk"), ("M0 s2", "m0_s2/analyze_fields.py", "ipk"),
    ("M0 s3", "m0_s3/run_tests.py", "ipk"),
    ("M1 s1", "m1_s1/encode_logic.py", "ipk"), ("M1 s2", "m1_s2/collect_reference.py", "ipk"),
    ("M1 s2", "m1_s2/build_b7.py", "ipk"), ("M1 s3", "m1_s3/readout_calc.py", "ipk"),
    ("M1 s4", "m1_s4/collect_phases.py", "ipk"), ("M1 s4", "m1_s4/logic_gates.py", "ipk"),
    ("M1 s5", "m1_s5/make_spec.py", "ipk"), ("M1 s5", "m1_s5/check_spec.py", "ipk"),
    ("M2 s1", "m2_s1/pic_boundary.py", "ipk"), ("M2 s2", "m2_s2/simulate.py", "ipk"),
    ("M2 s3", "m2_s3/build_layout.py", "ipk"), ("M2 s4", "m2_s4/review_layout.py", "ipk"),
    ("M2 s5", "m2_s5/build_chip.py", "ipk"), ("M2 s6", "m2_s6/verify_chip.py", "ipk"),
    ("M2 s7", "m2_s7/package.py", "ipk"),
]
ARCHIVED = re.compile(r"work/m0_s2/out/field_.*\.(json|npz)$")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p, base):
    return str(Path(p).relative_to(base)).replace("\\", "/")


# ---------------- ① 乾淨資料夾：只放程式、規則檔、設定與沿用的 Meep 結果 ----------------
def prepare():
    if DEST.exists():
        shutil.rmtree(DEST)
    for p in (ROOT / "work").rglob("*.py"):
        r = rel(p, ROOT)
        if "/out/" in r or "__pycache__" in r or r.startswith("work/m3_"):
            continue
        (DEST / r).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, DEST / r)
    shutil.copytree(ROOT / "work" / "common" / "drc", DEST / "work" / "common" / "drc")
    shutil.copyfile(ROOT / "EDA_paths.json", DEST / "EDA_paths.json")
    archived = {}
    for p in sorted((ROOT / "work" / "m0_s2" / "out").glob("field_*")):
        if p.suffix in (".json", ".npz"):
            d = DEST / rel(p, ROOT)
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, d)
            archived[rel(p, ROOT)] = sha(p)
    for d in ("sources", "spec", "course/figures"):
        (DEST / d).mkdir(parents=True, exist_ok=True)
    (DEST / "logs").mkdir()
    return archived


def run_step(script, kind, dest=DEST):
    path = dest / "work" / script
    if kind == "femwell":
        cmd = [CONDA, "run", "--no-capture-output", "-p", DEVSIM, "python", str(path)]
    else:
        cmd = [PY, str(path)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    t = time.time()
    r = subprocess.run(cmd, cwd=dest, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    log = dest / "logs" / (script.replace("/", "__") + ".log")
    log.write_text(f"$ {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))}\n\n{r.stdout}\n--- stderr ---\n{r.stderr}",
                   encoding="utf-8")
    return dict(script=script, kind=kind, rc=r.returncode, seconds=round(time.time() - t, 1),
                tail=(r.stderr.strip().splitlines() or [""])[-1][:200] if r.returncode else "")


# ---------------- ③ 比對 ----------------
RUNTIME_KEYS = {"runtime_s", "runtime", "seconds", "elapsed_s"}
HEX = re.compile(r"\b[0-9a-f]{64}\b")


def canon_gds(p):
    s, db = G.parse(str(p))
    ref = {r["sname"] for st in s.values() for r in st["srefs"]}
    tops = sorted(n for n in s if n not in ref)
    pl = []
    for t in tops:
        G.flatten(s, t, np.eye(2), np.zeros(2), pl)
    return sorted((l, tuple(np.round(q * db / 1e-6, 3).ravel())) for l, q in pl)


TOLSEEN = [0.0]                                       # 容差內最大的相對差（報告用）


def deep_diff(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        skip_size = "sha256" in a and "size" in a and a.get("sha256") == b.get("sha256")   # 清單：內容等價時檔案大小可不同
        for k in sorted(set(a) | set(b)):
            if k in RUNTIME_KEYS or (skip_size and k == "size"):
                continue
            if k not in a or k not in b:
                out.append(f"{path}/{k}（只在一邊）")
            else:
                deep_diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}（長度 {len(a)} vs {len(b)}）")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                deep_diff(x, y, f"{path}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        rd = abs(a - b) / max(1.0, abs(a), abs(b))
        if rd > 1e-9:
            out.append(f"{path}（{a} vs {b}）")
        else:
            TOLSEEN[0] = max(TOLSEEN[0], rd)
    elif a != b:
        out.append(f"{path}（{str(a)[:40]} vs {str(b)[:40]}）")
    return out


def lyrdb_items(txt):
    """KLayout 報告的標記：每個 <item> 的類別與座標，排序後比較（多執行緒時順序不固定）。"""
    items = re.findall(r"<item>(.*?)</item>", txt, flags=re.S)
    return sorted(re.sub(r"\s+", "", re.sub(r"<(multiplicity|tags|image|comment)>.*?</\1>", "", i, flags=re.S)) for i in items)


def compare(orig_root, new_root):
    files = []
    for p in sorted(new_root.rglob("*")):
        r = rel(p, new_root)
        if not p.is_file() or r.startswith("logs/") or "__pycache__" in r or r.endswith(".py") and r.startswith("work/"):
            continue
        if r.startswith("work/common/drc/") or r == "EDA_paths.json" or ARCHIVED.search(r) or r.endswith(".zip"):
            continue
        if r.endswith((".tmp", ".log")):
            continue
        files.append(r)
    old_root_s = [str(orig_root), str(orig_root).replace("\\", "/"), str(orig_root).replace("\\", "\\\\")]
    new_root_s = [str(new_root), str(new_root).replace("\\", "/"), str(new_root).replace("\\", "\\\\")]
    status, hmap = {}, {}

    def norm(txt):
        for n, o in zip(new_root_s, old_root_s):
            txt = txt.replace(n, o)
        return HEX.sub(lambda m: hmap.get(m.group(0), m.group(0)), txt)

    changed = True
    while changed:
        changed = False
        for r in files:
            if r in status and status[r][0] != "different":
                continue
            o, n = orig_root / r, new_root / r
            if not o.exists():
                status[r] = ("new_only", "原課程沒有這個檔案")
                continue
            if sha(o) == sha(n):
                st = ("identical", "")
            elif r.endswith(".gds"):
                st = ("equivalent", "GDS 多邊形相同（檔頭寫出時間不同）") if canon_gds(o) == canon_gds(n) else ("different", "多邊形不同")
            elif r.endswith(".png"):
                import matplotlib.image as mi
                a, b = mi.imread(o), mi.imread(n)
                if a.shape != b.shape:
                    st = ("different", "尺寸不同")
                else:
                    dmax = float(np.abs(a - b).max())
                    npx = int((np.abs(a - b).max(axis=-1) > 0).sum())
                    st = (("equivalent", "像素相同") if dmax == 0 else
                          ("equivalent", "反鋸齒差 1 個灰階（數值在容差內的差異）") if dmax <= 1 / 255 + 1e-6 else
                          ("different", f"{npx} 個像素不同，最大 {dmax * 255:.0f} 灰階"))
            elif r.endswith(".lyrdb"):
                lo, ln = lyrdb_items(o.read_text(encoding="utf-8")), lyrdb_items(norm(n.read_text(encoding="utf-8")))
                st = ("equivalent", "DRC 標記相同（排序後比對；路徑與標記順序不計）") if lo == ln else ("different", "DRC 標記不同")
            else:
                to = o.read_text(encoding="utf-8-sig", errors="replace")
                tn = norm(n.read_text(encoding="utf-8-sig", errors="replace"))
                if to == tn:
                    st = ("equivalent", "路徑或已等價檔案的雜湊不同")
                elif r.endswith(".json"):
                    TOLSEEN[0] = 0.0
                    d = deep_diff(json.loads(to), json.loads(tn))
                    why = "只差執行時間或檔案大小" if TOLSEEN[0] == 0 else f"數值在容差內（最大相對差 {TOLSEEN[0]:.1e}）"
                    st = ("equivalent", why) if not d else ("different", "；".join(d[:4]))
                else:
                    st = ("different", "文字不同")
            status[r] = st
            if st[0] in ("identical", "equivalent"):
                hmap[sha(n)] = sha(o)
                changed = True
    return status


if __name__ == "__main__":
    if "--compare-only" in sys.argv:                  # 只重做比對（重建資料夾與執行紀錄沿用上次）
        prev = json.loads((HERE / "out" / "rebuild_report.json").read_text(encoding="utf-8"))
        archived, runs = prev["archived"], prev["runs"]
        t0 = time.time() - sum(r["seconds"] for r in runs)      # 總時間 = 上次的重跑時間 + 這次的比對
    else:
        archived = prepare()
        print("prepared", DEST, len(archived), "archived Meep files")
        runs = []
        for step, script, kind in STEPS:
            r = run_step(script, kind)
            r["step"] = step
            runs.append(r)
            print(f"{step:6s} {script:32s} rc={r['rc']} {r['seconds']:7.1f}s {r['tail']}")
            if r["rc"] != 0:
                break
    ok_run = all(r["rc"] == 0 for r in runs) and len(runs) == len(STEPS)
    status = compare(ROOT, DEST) if ok_run else {}
    cnt = {}
    for s, _ in status.values():
        cnt[s] = cnt.get(s, 0) + 1
    diff = {k: v[1] for k, v in status.items() if v[0] == "different"}
    print("compare", cnt, list(diff.items())[:5])

    # 關鍵驗收量（直接讀重建結果）
    def J(p):
        return json.loads((DEST / p).read_text(encoding="utf-8"))
    key = {}
    if ok_run:
        R5, S6, D7 = J("work/m2_s5/out/m2_s5_result.json"), J("work/m2_s6/out/signoff.json"), J("work/m2_s7/out/delivery_check.json")
        TT0, TT1 = json.loads((ROOT / "spec/truth_table.json").read_text(encoding="utf-8")), J("spec/truth_table.json")
        key = dict(
            phase_sha_same=J("spec/pic_spec.json")["phase_settings"]["sha256"] == json.loads((ROOT / "spec/pic_spec.json").read_text(encoding="utf-8"))["phase_settings"]["sha256"],
            truth_rows=len(TT1["rows"]), truth_max_dp_diff=max(abs(a["delta"] - b["delta"]) for a, b in zip(TT0["rows"], TT1["rows"])),
            truth_bits_same=all(a["bit"] == b["bit"] and a["target"] == b["target"] for a, b in zip(TT0["rows"], TT1["rows"])),
            chip_rows_ok=sum(16 - v["wrong_1550"] for v in R5["gates"].values()), chip_all_wl=all(v["all_ok"] for v in R5["gates"].values()),
            gds_same=status.get("work/m2_s6/out/b7_chip_checked.gds", ("?",))[0] in ("identical", "equivalent"),
            signoff_ok=S6["all_ok"], delivery_ok=D7["all_ok"], new_gds_sha=S6["sha256"],
            n_eff=J("work/m0_s2/out/m0_s2_result.json")["modes"]["te0"]["n_eff"],
            n_g=J("work/m0_s2/out/m0_s2_result.json")["modes"]["te0"]["n_g"])
    print("key", key)

    # ④ 故障注入：改相位檔一個值，下游必須停下；比對器必須抓到一個數值差異
    tamper = {}
    if ok_run:
        ph = DEST / "sources" / "b7_phases.json"
        raw = ph.read_text(encoding="utf-8")
        d = json.loads(raw)
        d["gates"]["XOR2"]["theta"][0] += 1e-3
        ph.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        r = run_step("m2_s2/simulate.py", "ipk")
        tamper["phase_file"] = dict(stopped=r["rc"] != 0, message=r["tail"])
        ph.write_text(raw, encoding="utf-8")
        tt = json.loads((ROOT / "spec" / "truth_table.json").read_text(encoding="utf-8"))
        tt2 = json.loads(json.dumps(tt))
        tt2["rows"][37]["delta"] += 1e-6
        tamper["comparator"] = dict(found=deep_diff(tt, tt2))
        print("tamper", tamper)

    rep = dict(step="M3 s1", date="2026-10-31", dest="work/m3_s1/out/rebuild", archived=archived, runs=runs, ok_run=ok_run,
               counts=cnt, different=diff, status={k: list(v) for k, v in status.items()}, key=key, tamper=tamper,
               total_s=round(time.time() - t0, 1))
    rep["all_ok"] = (ok_run and not diff and key.get("gds_same") and key.get("signoff_ok") and key.get("delivery_ok")
                     and key.get("truth_bits_same") and key.get("chip_rows_ok") == 80
                     and tamper.get("phase_file", {}).get("stopped") and bool(tamper.get("comparator", {}).get("found")))
    (HERE / "out" / "rebuild_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("all_ok", rep["all_ok"], "total", rep["total_s"], "s")
