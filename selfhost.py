# -*- coding: utf-8 -*-
"""外部配信網への参照を、自前配信（/vendor/）へ書き換える。build 後の public/ と check_deploy で共用する。

書き換えは冪等（何度かけても同じ）。原本（各科目の HTML）は触らず、配信物だけを書き換える。
"""
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(ROOT, "vendor")

FONT_TAGS = re.compile(
    r'<link rel="preconnect" href="https://fonts\.googleapis\.com">'
    r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>'
    r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2\?[^"]*">')
SUBS = [
    (re.compile(r"https://cdn\.jsdelivr\.net/npm/mathjax@3/es5/(tex-chtml|tex-mml-chtml)\.js"), r"/vendor/mathjax/\1.js"),
    (re.compile(r"https://cdn\.jsdelivr\.net/npm/katex@0\.16\.9/dist/"), "/vendor/katex/"),
]


def rewrite(html):
    html = FONT_TAGS.sub('<link rel="stylesheet" href="/vendor/fonts/fonts.css">', html)
    for rx, rep in SUBS:
        html = rx.sub(rep, html)
    return html


def install(public):
    """public/ の HTML を書き換え、vendor/ を public/vendor/ へ置く。"""
    if not os.path.isdir(V):
        raise SystemExit("vendor/ がありません。python -X utf8 fetch_vendor.py を先に実行してください")
    dst = os.path.join(public, "vendor")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(V, dst)
    n = 0
    for r, _, fs in os.walk(public):
        if os.path.relpath(r, public).split(os.sep)[0] == "vendor":
            continue
        for f in fs:
            if f.endswith(".html"):
                p = os.path.join(r, f)
                s = open(p, encoding="utf-8", newline="").read()
                t = rewrite(s)
                if t != s:
                    open(p, "w", encoding="utf-8", newline="").write(t)
                    n += 1
    return n
