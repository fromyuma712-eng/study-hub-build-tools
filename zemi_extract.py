# -*- coding: utf-8 -*-
"""専門演習の履修要項PDFから、担任者ごとの説明文を原文のまま取り出す（G1：文字層のある頁）。

語は変えない。PDFの段組みによる行の途中の改行だけをつなぎ、互換文字（⼈ など）は NFKC で通常の字に揃える。
出力：zemi.json（git 管理外）。画像頁（文字層なし）は "needs_transcription": true として残し、別工程で書き起こす。

    python -X utf8 zemi_extract.py <履修要項.pdf>
"""
import json
import os
import re
import sys
import unicodedata

import fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "zemi.json")
BULLET = re.compile(r"^\s*(•|・|□|■|◆|◇|○|●|※|【|＜|<|-|－|―|①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|\(?\d+\)|（\d+）|\d+[.．)）]\s|[A-Za-z]\)|STEP|Step)")
HEAD = re.compile(r"^\s*([0-9０-９])\s*[.．。]\s*([^\s。、：:]{1,15})\s*[：:]?\s*(.*)$")   # 番号＋短い題（テーマ・概要・…・最後に など）


def _compat(ch):
    o = ord(ch)
    # 康熙部首・CJK部首補助・CJK互換漢字だけを通常の字へ（①や全角記号は変えない）
    if 0x2E80 <= o <= 0x2FDF or 0xF900 <= o <= 0xFAFF:
        return unicodedata.normalize("NFKC", ch)
    return ch


def norm(s):
    return "".join(_compat(c) for c in s)


def join_lines(lines):
    """段組みの改行をつなぐ。lines は (文字列, 折り返しか) の組。折り返し（右端まで届いた行）の次の行だけを前の行につなぐ。
    箇条記号だけの行（•）は次の行と合わせる。空行は1つにまとめて残す。"""
    out, wrap_prev = [], False
    for raw, wrapped in lines:
        ln = raw.rstrip()
        if not ln.strip():
            if out and out[-1] != "":
                out.append("")
            wrap_prev = False
            continue
        if out and out[-1] == "•":        # 「•」だけの行は次の行と合わせる
            out[-1] = "• " + ln.strip()
            wrap_prev = wrapped
            continue
        if ln.strip() == "•":
            out.append("•")
            continue
        prev = out[-1] if out else ""
        if prev and wrap_prev and not BULLET.match(ln):
            sep = " " if re.search(r"[A-Za-z0-9,.]$", prev) and re.match(r"[A-Za-z0-9(]", ln.strip()) else ""
            out[-1] = prev + sep + ln.strip()
        else:
            out.append(ln.strip())
        wrap_prev = wrapped
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def parse_index(page):
    """p.4 の一覧（担任者・テーマ・分野・頁）。"""
    t = norm(page.get_text())
    lines = [l.strip() for l in t.splitlines() if l.strip()]
    lines = lines[lines.index("ページ") + 1:]
    fields = ("ビジネス・データサイエンス", "データサイエンス", "ビジネス")
    rows, buf = [], []
    for l in lines:
        m = re.match(r"^(.*?)(ビジネス・データサイエンス|データサイエンス|ビジネス)$", l)
        if l.isdigit() and buf and buf[-1] in fields:
            name_theme = buf[:-1]
            rows.append({"name_theme": name_theme, "field": buf[-1], "page": int(l)})
            buf = []
        elif m and m.group(1) and not l.isdigit() and l not in fields:
            buf += [m.group(1), m.group(2)]
        else:
            buf.append(l)
    out = []
    for r in rows:
        nt = r["name_theme"]
        name = nt[0]
        rest = nt[1:]
        reading = None
        if rest and re.match(r"^（.*）$", rest[0]):
            reading, rest = rest[0], rest[1:]
        theme = "".join(rest)
        if name.startswith("2027年度着任予定教員A"):
            theme = name.split("※", 1)[1].strip() + theme
            name = "2027年度着任予定教員A ※"
        out.append({"name": name, "reading": reading, "theme_index": theme, "field": r["field"], "page": r["page"]})
    return out


def page_lines(page):
    """(行の文字列, 折り返しか) の列。右端が本文の右端から 18pt 以内なら折り返しとみなす。"""
    raw = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            txt = "".join(sp["text"] for sp in l["spans"])
            raw.append((norm(txt), l["bbox"][2]))
    xs = sorted(x for t, x in raw if len(t.strip()) > 8)
    right = xs[int(len(xs) * 0.9)] if xs else 0
    # 頁内で3回以上現れる右端の位置＝段の右端（本文の右端と、画像の横の狭い段の右端）
    edges = []
    for x in sorted(x for t, x in raw if len(t.strip()) >= 8):
        if edges and x - edges[-1][-1] <= 4:
            edges[-1].append(x)
        else:
            edges.append([x])
    edges = [sum(e) / len(e) for e in edges if len(e) >= 3]
    out = []
    for i, (t, x) in enumerate(raw):
        full = bool(t.strip()) and x >= right - 18
        side = (len(t.strip()) >= 8 and any(abs(x - e) <= 6 for e in edges)
                and not re.search(r"[。！？」）)]\s*$", t))
        out.append((t, full or side))
    return out


def parse_page(page):
    lines = page_lines(page)
    while lines and (not lines[-1][0].strip() or lines[-1][0].strip().isdigit()):
        lines.pop()
    head = ""
    sections, cur = [], None
    for ln, wrapped in lines:
        s = ln.strip()
        if not head and re.match(r"^(担任者|担当者)\s*[：:]", s) and not any(x["title"] == "テーマ" for x in sections):
            head = s
            continue
        m = HEAD.match(s)
        nums = [int(unicodedata.normalize("NFKC", x["no"])) for x in sections if x["no"]]
        if m and int(unicodedata.normalize("NFKC", m.group(1))) != (nums[-1] + 1 if nums else 1):
            m = None   # 見出しは 1,2,3… の連番だけ（概要の中の番号付き箇条は見出しにしない）
        KNOWN = ("テーマ", "概要", "受講生への要望・留意事項", "受講生への要望", "留意事項", "問い合わせ方法", "問合せ方法")
        if m and m.group(2) not in KNOWN and (m.group(3).strip() or len(m.group(2)) > 10):
            m = None   # 既知の題でなければ「番号＋短い題」だけの行に限る（例：５．最後に）
        if m:
            cur = {"no": m.group(1), "title": m.group(2), "lines": []}
            if m.group(3).strip():
                cur["lines"].append((m.group(3).strip(), False))
            sections.append(cur)
            continue
        if cur is None:
            if not s:
                continue
            cur = {"no": "", "title": "（見出しなし）", "lines": []}
            sections.append(cur)
        # テーマは原文の改行をそのまま残す（副題・補足が別行になっているため）
        cur["lines"].append((ln, wrapped and cur["title"] != "テーマ"))
    return head, [{"no": x["no"], "title": x["title"], "text": join_lines(x["lines"])} for x in sections]


def main():
    pdf = sys.argv[1]
    d = fitz.open(pdf)
    idx = parse_index(d[3])
    teachers = []
    for r in idx:
        p = d[r["page"] - 1]
        raw_chars = len(re.sub(r"\s", "", p.get_text()))
        head, secs = parse_page(p)
        ok = raw_chars > 300 and any(s["title"] == "概要" for s in secs)
        teachers.append(dict(r, header=head, sections=secs if ok else [],
                             needs_transcription=not ok, raw_chars=raw_chars))
    out = {"source": "2027年度開講「専門演習１」履修要項（2026年10月19日版）", "extracted": "2026-10-20",
           "teachers": teachers}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("担任者 %d 名 / 書き起こしが要る頁: %s" % (len(teachers), [t["page"] for t in teachers if t["needs_transcription"]]))
    for t in teachers:
        print(t["page"], t["field"], t["name"], "|", [s["title"] for s in t["sections"]])


if __name__ == "__main__":
    main()
