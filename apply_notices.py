# -*- coding: utf-8 -*-
"""授業からのお知らせ（次回・小テスト・課題）と Tips を、講義まとめの各回へ差し込む。

正本は notices.json（科目名を含むので git 管理外）。各回の .block の末尾に
<aside class="o-notice" data-round="N"> として置く。何度実行しても同じ結果になる（既存は置き換え）。

    python -X utf8 apply_notices.py           # 差し込む
    python -X utf8 apply_notices.py --check   # 差し込まず、対応の取れない科目・回だけ報告

notices.json の形:
  {"courses": {"<科目>": {"<回>": {"next": 文字列|null, "quiz": 文字列|null,
                                  "tasks": [文字列], "tips": [文字列], "impression": 文字列, "source": 文字列}}}}
TIPS と感想（impression）は講義資料外の、Claude による助言・所感である（ページにもその旨を出す）。演習・課題の答えは書かない。
"""
import html
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import atomicio  # noqa: E402

DATA = os.path.join(ROOT, "notices.json")
import site_config as C  # noqa: E402
TERM_DIR = os.path.join(C.SRC_BASE, "2026_秋")   # 講義まとめの原本の置き場（site_config に従う）
ASIDE_RE = r'[ \t]*<aside class="o-notice" data-round="%s">.*?</aside>[ \t]*\r?\n?'


def nfc(s):
    return unicodedata.normalize("NFC", s)


def note_path(course):
    for d in os.listdir(TERM_DIR):
        if nfc(d) == nfc(course):
            p = os.path.join(TERM_DIR, d, "講義まとめ.html")
            return p if os.path.isfile(p) else None
    return None


def esc(s):
    return html.escape(s or "", quote=False)


def render(rnd, n):
    rows = []
    if n.get("next"):
        rows.append(("次回", [n["next"]]))
    if n.get("quiz"):
        rows.append(("小テスト", [n["quiz"]]))
    if n.get("tasks"):
        rows.append(("課題", n["tasks"]))
    out = ['<aside class="o-notice" data-round="%s">' % rnd,
           '<div class="o-nh">NOTICE <b>次回・小テスト・課題</b></div>']
    if rows:
        out.append('<dl class="o-nl">' + "".join(
            "<dt>%s</dt><dd>%s</dd>" % (k, "".join("<p>%s</p>" % esc(v) for v in vs)) for k, vs in rows) + "</dl>")
    else:
        out.append('<p class="o-nempty">この回の資料と講義では、次回・小テスト・課題についての言及を確認できなかった。</p>')
    if n.get("tips"):
        out.append('<div class="o-tips"><div class="o-nh">TIPS <b>Claude の突っ込み</b></div><ul>'
                   + "".join("<li>%s</li>" % esc(t) for t in n["tips"]) + "</ul></div>")
    if n.get("impression"):
        out.append('<div class="o-imp"><div class="o-nh">IMPRESSION <b>Claude の感想</b></div><p>'
                   + esc(n["impression"]) + "</p></div>")
    src = ("出典：" + esc(n["source"]) + "。") if n.get("source") else ""
    out.append('<p class="o-nsrc">' + src + "TIPS と感想は講義資料外の、Claude による助言・所感である。</p>")
    out.append("</aside>")
    return "".join(out)


def section_span(s, rnd):
    m = re.search(r'<h2[^>]*\sid="s%s"' % rnd, s)
    if not m:
        return None
    nxt = re.search(r'<h2[\s>]|<div class="note', s[m.end():])
    return m.start(), (m.end() + nxt.start()) if nxt else len(s)


def apply(course, rounds, check=False):
    p = note_path(course)
    if not p:
        return ["科目の講義まとめが見つからない: " + course]
    raw = open(p, "rb").read().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    s = raw
    problems = []
    for rnd in sorted(rounds, key=int):
        s = re.sub(ASIDE_RE % rnd, "", s, flags=re.S)
        span = section_span(s, rnd)
        if not span:
            problems.append("%s 第%s回: 講義まとめに回が無い" % (course, rnd))
            continue
        a, b = span
        closes = [m for m in re.finditer(r"\r?\n[ \t]*</div>[ \t]*(?=\r?\n|$)", s[a:b])]
        if not closes:
            problems.append("%s 第%s回: 回の .block の終わりが見つからない" % (course, rnd))
            continue
        at = a + closes[-1].start()
        s = s[:at] + nl + render(rnd, rounds[rnd]) + s[at:]
    if not check and s != raw:
        atomicio.write_text(p, s)
    return problems


def main():
    check = "--check" in sys.argv
    if not os.path.isfile(DATA):
        sys.exit("notices.json がない")
    d = json.load(open(DATA, encoding="utf-8"))
    probs, n = [], 0
    for course, rounds in d.get("courses", {}).items():
        probs += apply(course, rounds, check)
        n += len(rounds)
    for x in probs:
        print("  [!] " + x)
    print("notices: %d 科目 / %d 回%s" % (len(d.get("courses", {})), n, "（検査のみ）" if check else ""))
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
