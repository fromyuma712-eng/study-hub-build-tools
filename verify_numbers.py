# -*- coding: utf-8 -*-
"""講義まとめの各回に書かれた数値・日付が、その回の原本（資料フォルダの PDF・pptx・文字起こし）に現れるかを調べる。

講義まとめを書いたあとの取り違え（桁・年・回次・順位など）を機械で拾うための検査。内容の正しさそのものは判定しない。
    python -X utf8 verify_numbers.py [科目名の一部] [--all]   （既定は 2026_秋）

見るのは、数字（2桁以上、または小数・単位つき）。次は除く: 図、〔講義での口頭説明〕〔講義資料外の補足〕の段落、回番号・節番号・年号の一部。
「原本に無い数」は、(1) 計算した値、(2) 図から読み取った概数、(3) 資料に無い数、のどれか。(3) だけが誤りなので目で確かめる。
"""
import glob
import json
import os
import re
import sys
import unicodedata
import zipfile

import fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
KANSAI = os.path.expanduser("~/Claude/kansai-uni")
TOKEN = re.compile(r"\d+(?:[.,]\d+)*(?:%|円|万|億|千|年|月|日|回|頁|人|件|枚|個|台|時間|分|秒|歳|ドル|倍|倍)?")


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def squash(s):
    return re.sub(r"[\s,，]", "", nfkc(s))


def pdf_text(p):
    d = fitz.open(p)
    return "\n".join(pg.get_text() for pg in d)


def pptx_text(p):
    z = zipfile.ZipFile(p)
    out = []
    for n in z.namelist():
        if re.match(r"ppt/slides/slide\d+\.xml$", n):
            out.append(" ".join(re.findall(r"<a:t>([^<]*)</a:t>", z.read(n).decode("utf8"))))
    return "\n".join(out)


def source_text(folder, n):
    t = []
    for f in sorted(glob.glob(os.path.join(folder, "資料", "第%d回_*" % n))):
        if os.path.isdir(f):
            continue
        try:
            if f.lower().endswith(".pdf"):
                t.append(pdf_text(f))
            elif f.lower().endswith(".pptx"):
                t.append(pptx_text(f))
        except Exception:
            pass
        ex = os.path.join(ROOT, ".extract", os.path.splitext(os.path.basename(f))[0], "text.txt")
        if os.path.isfile(ex):
            t.append(open(ex, encoding="utf-8").read())
    return squash("\n".join(t))


def rounds(html):
    parts = re.split(r'(<h2 id="s(\d+)">)', html)
    out = {}
    for i in range(1, len(parts) - 2, 3):
        out[int(parts[i + 1])] = parts[i + 2]
    return out


def clean(block):
    block = re.sub(r"<figure.*?</figure>", " ", block, flags=re.S)
    block = re.sub(r'<div class="pt">(?:(?!</div>).)*?〔講義での口頭説明〕.*?</div>', " ", block, flags=re.S)
    block = re.sub(r'<div class="pt">(?:(?!</div>).)*?〔講義資料外の補足〕.*?</div>', " ", block, flags=re.S)
    block = re.sub(r"<!--.*?-->", " ", block, flags=re.S)
    block = re.sub(r"<script.*?</script>|<style.*?</style>", " ", block, flags=re.S)
    block = re.sub(r"<[^>]+>", " ", block)
    return nfkc(re.sub(r"&[a-z]+;", " ", block))


def check_course(name):
    folder = os.path.join(KANSAI, "2026_秋", name)
    f = os.path.join(folder, "講義まとめ.html")
    if not os.path.isfile(f):
        return []
    res = []
    for n, blk in rounds(open(f, encoding="utf-8").read()).items():
        src = source_text(folder, n)
        if not src:
            res.append((name, n, None, []))
            continue
        text = clean(blk)
        miss = []
        for m in sorted(set(TOKEN.findall(text))):
            digits = re.sub(r"\D", "", m)
            if len(digits) < 2 and not re.search(r"[.%]", m):
                continue
            if squash(m) in src:
                continue
            core = re.sub(r"[^\d.]", "", m)
            if core and core in src:
                continue
            miss.append(m)
        res.append((name, n, len(src), miss))
    return res


def main():
    key = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = os.path.join(KANSAI, "2026_秋")
    for c in sorted(os.listdir(base)):
        if c.startswith("_") or (key and key[0] not in c):
            continue
        for name, n, ln, miss in check_course(c):
            if ln is None:
                print("%-24s 第%d回  原本なし（検査せず）" % (name[:22], n))
            else:
                print("%-24s 第%d回  原本に無い数 %2d: %s" % (name[:22], n, len(miss), " ".join(miss[:40])))


if __name__ == "__main__":
    main()
