"""GDS 統計（M2 s7 Virtuoso／Calibre 段）：每層多邊形數、最大頂點數、cell／參照數、各種元素數。

只讀 GDS 本身，不需要 IPKISS 或 KLayout。
用法：python gds_stats.py <gds> [<gds> ...]   → 印出 JSON
也可 import：stats(path) 回傳 dict。
"""
import json
import struct
import sys
from collections import Counter
from pathlib import Path

KIND = {0x0800: "boundary", 0x0900: "path", 0x0A00: "sref", 0x0B00: "aref", 0x0C00: "text", 0x2D00: "box"}


def stats(path):
    data = Path(path).read_bytes()
    i, cells, kinds = 0, 0, Counter()
    per_layer, max_vert, layer = Counter(), Counter(), None
    kind = None
    texts = []
    dtypes = set()
    while i < len(data):
        ln = struct.unpack(">H", data[i:i + 2])[0]
        if ln == 0:
            break
        code = (data[i + 2] << 8) | data[i + 3]
        pay = data[i + 4:i + ln]
        if code == 0x0502:
            cells += 1
        elif code in KIND:
            kind = KIND[code]
            kinds[kind] += 1
        elif code == 0x0D02:
            layer = struct.unpack(">h", pay[:2])[0]
        elif code == 0x0E02 and kind == "boundary":
            dtypes.add((layer, struct.unpack(">h", pay[:2])[0]))
        elif code == 0x1003 and kind == "boundary":
            n = len(pay) // 8                       # 點數（含閉合點）
            per_layer[layer] += 1
            max_vert[layer] = max(max_vert[layer], n)
        elif code == 0x1906 and kind == "text":
            texts.append(pay.split(b"\x00")[0].decode("ascii", "ignore"))
        elif code == 0x1100:
            kind = None
        i += ln
    return dict(cells=cells, elements=dict(kinds), polygons_per_layer={str(k): v for k, v in sorted(per_layer.items())},
                max_points_per_layer={str(k): v for k, v in sorted(max_vert.items())},
                layer_datatypes=sorted(f"{l}/{d}" for l, d in dtypes), texts=sorted(texts))


if __name__ == "__main__":
    print(json.dumps({Path(p).name: stats(p) for p in sys.argv[1:]}, ensure_ascii=False, indent=1))
