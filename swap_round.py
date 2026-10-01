# -*- coding: utf-8 -*-
"""講義まとめの1回分（h2 から次の h2／作成方針の note の直前まで）を、書き直した断片で差し替える。

    python -X utf8 swap_round.py <講義まとめ.html> <断片.html> [--dry]

- 断片は `<h2 id="...">` で始まり、その回の block の閉じで終わる。h2 の id が原本に1回だけあること。
- 差し替え範囲に含まれていた図のうち、断片に無いものは外れる（外れた data-fig を表示する）。
- 改行コードは原本に合わせる。書き込み前のファイルは呼び出し側でバックアップしておくこと。
"""
import re
import sys

import atomicio


def main():
    page, frag_path = sys.argv[1], sys.argv[2]
    dry = "--dry" in sys.argv
    raw = open(page, "rb").read().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    frag = open(frag_path, encoding="utf-8").read().strip().replace("\r\n", "\n")
    m = re.match(r'<h2 id="([^"]+)"', frag)
    if not m:
        sys.exit("断片が <h2 id=...> で始まっていない")
    hid = m.group(1)
    if frag.count("<div") != frag.count("</div>"):
        sys.exit("断片の div の開閉が合わない")
    key = '<h2 id="%s"' % hid
    if raw.count(key) != 1:
        sys.exit("原本に %s が %d 回ある" % (key, raw.count(key)))
    a = raw.index(key)
    nxt = [raw.find(t, a + 1) for t in ("\n<h2 ", "\r\n<h2 ", '\n<div class="note', '\r\n<div class="note')]
    nxt = [x for x in nxt if x != -1]
    b = min(nxt)
    old = raw[a:b]
    old_figs = set(re.findall(r'data-fig="([^"]+)"', old))
    new_figs = set(re.findall(r'data-fig="([^"]+)"', frag))
    out = raw[:a] + frag.replace("\n", nl) + nl + nl + raw[b:].lstrip("\r\n")
    print("%s: 旧 %d字 → 新 %d字 / 外れた図 %s / 新しい図 %s" % (
        hid, len(old), len(frag), sorted(old_figs - new_figs) or "なし", sorted(new_figs - old_figs) or "なし"))
    if not dry:
        atomicio.write_text(page, out)


if __name__ == "__main__":
    main()
