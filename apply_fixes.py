# -*- coding: utf-8 -*-
"""校正の修正案（JSON）を講義まとめの原本へ適用する。親が根拠を確かめた案だけを通す。

    python -X utf8 apply_fixes.py <fixes.json> --ids 1,2,5      # 指定した id だけ適用
    python -X utf8 apply_fixes.py <fixes.json> --ids 1,2 --dry   # 置き換え前後を表示するだけ

JSON の形（作業者が出す）:
    {"file": "<SRC_BASE からの相対パス>", "fixes": [{"id": 1, "old": "...", "new": "..."}, ...]}

- old は原本にちょうど1回だけ現れなければならない。0回・2回以上なら何も書かずに止まる。
- 図（<figure class="o-fig">…</figure>）と外観の層（OBSERVATORY-SKIN）の中は書き換えない。
- 改行コードは原本に合わせる（atomicio.write_text は受け取った文字列をそのまま書く）。
"""
import json
import os
import re
import sys

import atomicio
from siteconf import C

PROTECTED = re.compile(r'<figure class="o-fig".*?</figure>|<!-- OBSERVATORY-SKIN:(\w+)[^>]*-->.*?<!-- /OBSERVATORY-SKIN:\1 -->', re.S)


def protected_spans(s):
    return [(m.start(), m.end()) for m in PROTECTED.finditer(s)]


def main():
    args = sys.argv[1:]
    src = args[0]
    ids = {int(x) for x in args[args.index("--ids") + 1].split(",")} if "--ids" in args else set()
    dry = "--dry" in args
    data = json.load(open(src, encoding="utf-8"))
    path = data["file"] if os.path.isabs(data["file"]) else os.path.join(C.SRC_BASE, data["file"])
    s = open(path, "rb").read().decode("utf-8")
    todo = [f for f in data["fixes"] if f["id"] in ids]
    missing = ids - {f["id"] for f in todo}
    if missing:
        sys.exit("id が JSON に無い: %s" % sorted(missing))
    errs = []
    for f in todo:
        n = s.count(f["old"])
        if n != 1:
            errs.append("id %d: old が %d 回現れる" % (f["id"], n))
            continue
        i = s.index(f["old"])
        if any(a <= i < b for a, b in protected_spans(s)):
            errs.append("id %d: 図か外観の層の中にある" % f["id"])
    if errs:
        sys.exit("\n".join(errs))
    for f in todo:
        if dry:
            print("--- id %d\n- %s\n+ %s" % (f["id"], f["old"], f["new"]))
        s = s.replace(f["old"], f["new"], 1)
    if not dry:
        atomicio.write_text(path, s)
    print("%s: %d 件%s" % (os.path.basename(os.path.dirname(path)), len(todo), "（試行）" if dry else "適用"))


if __name__ == "__main__":
    main()
