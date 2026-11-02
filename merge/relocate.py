"""把複製到 C:\\LAB\\Lab06b 的兩套程式裡寫死的舊課程根目錄改成新位置。
只改程式與設定檔；log、證據、out/、history/、delivery/ 保留原文當紀錄。可重複執行（第二次不會再改）。
用法：C:\\luceda\\luceda_2026033\\envs\\ipkiss3\\python.exe C:\\LAB\\Lab06b\\merge\\relocate.py
"""
import re
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
CODE = {".py", ".ps1", ".sh", ".tcl", ".il", ".cjs", ".drc", ".lydrc", ".svrf"}
SKIP_DIRS = {"out", "history", "reference", "delivery", "tools", "evidence", "__pycache__"}


def rules(old_parts, new_parts):
    out = []
    # 依序處理 4、2、1 個反斜線與正斜線的寫法
    for sep_re, sep in ((r"\\\\\\\\", "\\\\\\\\"), (r"\\\\", "\\\\"), (r"\\", "\\"), ("/", "/")):
        old = "C:" + sep_re + sep_re.join(map(re.escape, old_parts)) + r"(?![A-Za-z0-9_])"
        new = "C:" + sep + sep.join(new_parts)
        out.append((re.compile(old), new.replace("\\", "\\\\")))
    out.append((re.compile("/mnt/c/" + "/".join(old_parts) + r"(?![A-Za-z0-9_])"),
                "/mnt/c/" + "/".join(new_parts)))
    return out


def files(root, extra, skip_trials):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).parts
        if any(d in SKIP_DIRS for d in rel[:-1]):
            continue
        if skip_trials and len(rel) > 3 and rel[0] == "work" and rel[2] == "work":
            continue  # work/<step>/work/ 是當時的試跑副本，保留原文
        if p.name in ("finalize.py", "backup_record.json"):
            continue  # 一次性紀錄
        if p.suffix.lower() in CODE or p.relative_to(root).as_posix() in extra:
            yield p


HEX64 = re.compile(r"[0-9a-f]{64}")
QUOTED = re.compile(r'"([^"\\]+\.(?:py|ps1|sh|tcl|il|cjs|svrf|json))"')


def pinned(root):
    """另一版的程式會核對自己記錄的來源 SHA-256；被記錄過的檔案一律不改，以免核對失敗。"""
    keep = set()
    for j in root.rglob("*.json"):
        rel = j.relative_to(root).parts
        if any(d in {"tools", "history", "reference"} for d in rel[:-1]):
            continue
        try:
            t = j.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        if HEX64.search(t):
            keep.update(s.replace("\\\\", "/").replace("\\", "/") for s in QUOTED.findall(t))
    return keep


def apply(root, rs, extra, skip_trials, keep=frozenset()):
    changed = []
    for p in files(root, extra, skip_trials):
        if p.relative_to(root).as_posix() in keep:
            continue
        try:
            t = p.read_bytes().decode("utf-8")  # 不轉換換行
        except UnicodeDecodeError:
            continue
        n = t
        for rx, rep in rs:
            n = rx.sub(rep, n)
        if n != t:
            p.write_bytes(n.encode("utf-8"))
            changed.append(p.relative_to(LAB).as_posix())
    return changed


if __name__ == "__main__":
    a = apply(LAB / "impl_a", rules(["EDA_Claude"], ["LAB", "Lab06b", "impl_a"]), {"EDA_paths.json"}, False)
    keep = pinned(LAB / "impl_b")
    b = apply(LAB / "impl_b", rules(["EDA_Codex", "Lab06b"], ["LAB", "Lab06b", "impl_b"]),
              {"EDA_paths.json", "config/course.json"}, True, keep)
    print(len(a), "files in impl_a;", len(b), "files in impl_b;", len(keep), "hash-pinned paths left as is")
    for x in a + b:
        print(" ", x)
