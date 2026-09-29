# -*- coding: utf-8 -*-
"""講義まとめの図（.o-fig）を機械的に検査する（RUNBOOK §2-2）。

    python -X utf8 check_figs.py              # 全頁
    python -X utf8 check_figs.py 科目名        # 科目名の部分一致で絞り込み

FAIL（直すまで完了にしない）:
- data-fig が無い・頁の中で重複・書式が「英小文字と数字-英小文字」でない
- SVG が XML として壊れている / viewBox が無い
- 決められた class 以外を使っている、色（fill・stroke・style・color）を直接書いている
- 文字が viewBox からはみ出す、文字どうしが重なる（文字幅は figkit.text_width の見積もり）
- figcaption が空
- 1つの回（h2 の節）に図が4枚以上

内容の正しさ（講義にある事柄か）は見ない。それは執筆の規則と親の目視で担保する。
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

import figkit
from siteconf import C

ROOT = os.path.dirname(os.path.abspath(__file__))
ALLOWED_CLASS = {"bx", "ax", "gr", "ln", "ln2", "ar", "ah", "dot", "em", "emf", "e", "t"}
ALLOWED_TAG = {"svg", "g", "rect", "path", "text", "circle", "line", "polyline", "polygon", "ellipse", "tspan"}
COLOR_ATTR = {"fill", "stroke", "style", "color"}
FID_RE = re.compile(r"^[a-z0-9]+-[a-z0-9-]+$")
FIG_RE = re.compile(r'<figure class="o-fig"(.*?)</figure>', re.S)
MAX_PER_ROUND = 3


def translate_of(el_chain):
    dx = dy = 0.0
    for el in el_chain:
        m = re.search(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", el.get("transform", ""))
        if m:
            dx += float(m.group(1))
            dy += float(m.group(2))
    return dx, dy


def text_boxes(svg):
    """(x0, y0, x1, y1, 文字) の一覧。見積もりなので少し内側で判定する。"""
    out = []

    def walk(el, chain):
        chain = chain + [el]
        tag = el.tag.split("}")[-1]
        if tag == "text":
            s = "".join(el.itertext())
            cls = el.get("class", "")
            size = figkit.FONT.get(cls, 12.0)
            w = figkit.text_width(s, cls)
            dx, dy = translate_of(chain)
            x, y = float(el.get("x", 0)) + dx, float(el.get("y", 0)) + dy
            a = el.get("text-anchor", "start")
            x0 = x - w / 2 if a == "middle" else (x - w if a == "end" else x)
            out.append((x0, y - size * 0.85, x0 + w, y + size * 0.2, s))
        for ch in el:
            walk(ch, chain)
    walk(svg, [])
    return out


def check_figure(fig_html, where):
    errs = []
    m = re.search(r'data-fig="([^"]*)"', fig_html)
    fid = m.group(1) if m else ""
    if not fid:
        errs.append("%s: data-fig が無い" % where)
    elif not FID_RE.match(fid):
        errs.append("%s: data-fig '%s' の書式が不正（英小文字と数字-英小文字）" % (where, fid))
    cap = re.search(r"<figcaption>(.*?)</figcaption>", fig_html, re.S)
    if not cap or not re.sub(r"<[^>]+>", "", cap.group(1)).strip():
        errs.append("%s[%s]: figcaption が空" % (where, fid))
    sm = re.search(r"<svg\b.*?</svg>", fig_html, re.S)
    if not sm:
        return fid, errs + ["%s[%s]: svg が無い" % (where, fid)]
    try:
        svg = ET.fromstring(sm.group(0))
    except ET.ParseError as e:
        return fid, errs + ["%s[%s]: SVG が壊れている（%s）" % (where, fid, e)]
    vb = svg.get("viewBox")
    if not vb:
        return fid, errs + ["%s[%s]: viewBox が無い" % (where, fid)]
    _, _, W, H = [float(v) for v in vb.split()]
    for el in svg.iter():
        tag = el.tag.split("}")[-1]
        if tag not in ALLOWED_TAG:
            errs.append("%s[%s]: 使えない要素 <%s>" % (where, fid, tag))
        for c in el.get("class", "").split():
            if c not in ALLOWED_CLASS:
                errs.append("%s[%s]: 決められていない class '%s'" % (where, fid, c))
        for a in COLOR_ATTR & set(el.keys()):
            errs.append("%s[%s]: 色を直接書いている（%s）。class で指定する" % (where, fid, a))
    boxes = text_boxes(svg)
    for x0, y0, x1, y1, s in boxes:
        # 図の枠には余白があり、SVG は枠外も描くので 4px までは許す
        if x0 < -4 or x1 > W + 4 or y0 < -4 or y1 > H + 4:
            errs.append("%s[%s]: 文字が枠外へはみ出す「%s」" % (where, fid, s[:20]))
    for i in range(len(boxes)):
        a = boxes[i]
        for b in boxes[i + 1:]:
            ix = min(a[2], b[2]) - max(a[0], b[0])
            iy = min(a[3], b[3]) - max(a[1], b[1])
            if ix > 3 and iy > 3:
                errs.append("%s[%s]: 文字が重なる「%s」と「%s」" % (where, fid, a[4][:14], b[4][:14]))
    return fid, errs


def check_page(course, path):
    s = open(path, encoding="utf-8").read()
    errs, seen, n = [], set(), 0
    sections = re.split(r"<h2\b", s)
    for k, sec in enumerate(sections[1:], 1):
        head = re.sub(r"<[^>]+>", "", sec[: sec.find("</h2>")]).split(">", 1)[-1][:24]
        figs = FIG_RE.findall(sec)
        if len(figs) > MAX_PER_ROUND:
            errs.append("%s: 「%s」の節に図が %d 枚（上限 %d）" % (course, head, len(figs), MAX_PER_ROUND))
        for f in figs:
            n += 1
            fid, e = check_figure(f, course)
            errs += e
            if fid in seen:
                errs.append("%s: data-fig '%s' が重複" % (course, fid))
            seen.add(fid)
    return n, errs


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    total, fails, pages = 0, [], 0
    for it in b.MANIFEST:
        if "src" not in it:
            continue
        if want and not any(w in it["course"] for w in want):
            continue
        path = it["src"] if os.path.isabs(it["src"]) else os.path.join(b.SRC_BASE, it["src"])
        if not os.path.isfile(path):
            continue
        if "--ctx-bar" not in open(path, encoding="utf-8").read():
            continue  # 講義まとめの共通雛形でない頁（問題集などのアプリ）は対象外
        n, errs = check_page(it["course"], path)
        pages += 1
        total += n
        print("%-24s 図 %3d 枚  %s" % (it["course"], n, "FAIL %d" % len(errs) if errs else "OK"))
        fails += errs
    for e in fails:
        print("  [FAIL] " + e)
    print("\n検査 %d 頁 / 図 %d 枚 / FAIL %d" % (pages, total, len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
