# -*- coding: utf-8 -*-
"""講義まとめの原本へ図を差し込む（何度実行しても同じ結果になる）。

    from insert_figs import insert
    insert(html_path, [("<b>アムダールの法則</b>", fig_html), ...])

- 第1要素は差し込む位置の目印。原本にちょうど1回だけ現れる文字列（通常は項目の見出し `<b>…</b>`）とし、
  その文字列を含む項目（div）の閉じタグの直後に図を置く。
- 同じ data-fig の図が既にあれば、その図を置き換える（位置は動かさない）。
- 改行コードは原本に合わせる。本文の文字は一切書き換えない。
"""
import re

import atomicio

FIG_RE = re.compile(r'<figure class="o-fig" data-fig="([^"]+)".*?</figure>', re.S)


def _close_of(s, i):
    """位置 i を含む <div> の閉じタグの直後の位置を返す（入れ子を数える）。"""
    start = s.rfind("<div", 0, i)
    depth, pos = 0, start
    tag = re.compile(r"<(/?)div\b[^>]*>")
    for m in tag.finditer(s, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
        pos = m.end()
    raise ValueError("div の閉じが見つからない")


def insert(path, items):
    raw = open(path, "rb").read().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    s = raw
    added = replaced = 0
    for anchor, html in items:
        fid = re.search(r'data-fig="([^"]+)"', html).group(1)
        existing = [m for m in FIG_RE.finditer(s) if m.group(1) == fid]
        if existing:
            m = existing[0]
            s = s[:m.start()] + html + s[m.end():]
            replaced += 1
            continue
        n = s.count(anchor)
        if n != 1:
            raise ValueError("目印が %d 回現れる（1回でなければならない）: %s" % (n, anchor))
        j = _close_of(s, s.index(anchor))
        s = s[:j] + nl + "  " + html + s[j:]
        added += 1
    atomicio.write_text(path, s)
    return added, replaced


def remove(path, fids):
    """指定した data-fig の図を外す（やり直し用）。"""
    s = open(path, "rb").read().decode("utf-8")
    nl = "\r\n" if "\r\n" in s else "\n"
    for fid in fids:
        s = re.sub(r"(\r?\n  )?<figure class=\"o-fig\" data-fig=\"%s\".*?</figure>" % re.escape(fid), "", s, flags=re.S)
    atomicio.write_text(path, s)
