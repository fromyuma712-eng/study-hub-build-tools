# -*- coding: utf-8 -*-
"""
網羅性検査の対象表 `coverage_manifest.json` を生成する。

「PDF ↔ 回次 ↔ HTMLの節」の対応は科目ごとに規則が異なるため、自動生成の
のちに人手で確定する方式を採る（2026/8/23 利用者決定）。

科目ごとの特殊事情（番号のずれ・機械では回次を決められない科目）は、
授業を特定しうるため site_config.py（非公開）の COVERAGE_OFFSET / COVERAGE_MANUAL に置く。

テキスト層の無いPDF（実測 536件中92件・17%）は見出しを抽出できないため
`NOT_APPLICABLE` とし、MISS の集計から外す。

使い方:
    python -X utf8 gen_coverage_manifest.py        # 生成（既存の確定値は保持）
    python -X utf8 check_coverage.py --all         # 生成後に全件走査
"""
import unicodedata
import atomicio
import glob
import importlib.util
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
# 講義資料の場所は site_config.py（非公開）が決める
from siteconf import C  # noqa: E402
SRC_BASE = C.SRC_BASE
OUT = os.path.join(ROOT, "coverage_manifest.json")
MIN_CHARS_PER_PAGE = 50          # これ未満は画像PDFとみなす

_s = importlib.util.spec_from_file_location("bm", os.path.join(ROOT, "build.py"))
bm = importlib.util.module_from_spec(_s)
_s.loader.exec_module(bm)

# ファイル名の番号と回次がずれる科目。値は「回次 = ファイル番号 + offset」
OFFSET = C.COVERAGE_OFFSET
# 想定最終回。ファイル名の数字がこれを超えるならハッシュや年号の混入である
EXPECTED_LAST = {k: v["value"] for k, v in json.load(
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "exceptions.json"),
         encoding="utf-8"))["expected_last_round"].items() if not k.startswith("_")}
# 自動対応をあきらめる科目（対応規則が一様でない）。人手で rows を書く。
MANUAL = C.COVERAGE_MANUAL



def headline_spans(pdf, pages=2, take=14):
    """PDF冒頭の、フォントが大きい順の行を返す。表紙の表題を拾うため。"""
    try:
        d = fitz.open(pdf)
    except Exception:
        return []
    got = []
    try:
        for pg in list(d)[:pages]:
            for b in pg.get_text('dict')['blocks']:
                for ln in b.get('lines', []):
                    for sp in ln['spans']:
                        t = sp['text'].strip()
                        if len(t) >= 2:
                            got.append((sp['size'], t))
    except Exception:
        return []
    finally:
        d.close()
    got.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, t in got:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= take:
            break
    return out


def round_from_pdf(pdf, course, last):
    """PDF表紙から回次を取り出す。(回次, 根拠文字列) か (None, None)。

    ファイル名がハッシュや連番でも、表紙には「科目名第１回ガイダンス」
    「科目名６」のように回次が書かれていることが多い。**ファイル名より
    確かな根拠である**(2026/8/24)。

    「第1問」「全１３回」のような紛らわしい語を拾わないよう、
    拾うのは表紙の大きな文字に限り、想定最終回を超える数は捨てる。
    """
    lines = headline_spans(pdf)
    joined = ' / '.join(lines[:6])
    for t in lines:
        u = unicodedata.normalize('NFKC', t)
        m = re.search(r'第\s*(\d+)\s*回', u)
        if m:
            n = int(m.group(1))
            if 1 <= n <= last:
                return n, t
        # 「科目名６」「科目名第14」のように科目名に数字が続く形
        m = re.fullmatch(re.escape(course) + r'\s*第?\s*(\d+)\s*回?', u)
        if m:
            n = int(m.group(1))
            if 1 <= n <= last:
                return n, t
    return None, joined


def round_from_name(base, last):
    """ファイル名から回次を取り出す。決められなければ None を返し人手へ回す。

    旧版は「最後の数字」を採っていた。実データでは末尾に年号や版数が付くため
    壊れていた(2026/8/24 発見)。
        第10回　ユダヤ民族とアメリカ2024.pdf   -> 2024
        46bf82cda43194f718d2e8ea911855fd.pdf -> 911855

    数字を拾う規則は、強い順に次の4段である。**推測できないものは推測しない**
    ——ハッシュ名に無理やり回次を割り当てるより、人手へ回すほうが安全である。
    """
    stem = os.path.splitext(base)[0]

    # (1) 「第N回」の明示。最も強い
    m = re.search(r'第\s*([0-9\uff10-\uff19]+)\s*回', stem)
    if m:
        return int(unicodedata.normalize('NFKC', m.group(1)))

    # (2) ハッシュ名は回次を持たない。数字を拾えば必ず誤りになる
    if re.fullmatch(r'[0-9a-f]{8,}', stem, re.I):
        return None

    # (3) 「5of15」形式。曜日時限(「火5」)より後ろに現れるため、
    #     単純に先頭の数字を採ると時限を回次と誤る
    m = re.search(r'(\d+)\s*of\s*(\d+)', stem, re.I)
    if m:
        n, tot = int(m.group(1)), int(m.group(2))
        if 1 <= n <= tot:
            return n

    # (4) 年号と想定最終回超えを捨て、残った先頭の数
    cand = []
    for t in re.findall(r'\d+', stem):
        v = int(t)
        if 1900 <= v <= 2100:
            continue
        if v < 1 or v > last:
            continue
        cand.append(v)
    return cand[0] if cand else None

def page_chars(path):
    try:
        d = fitz.open(path)
        n, t = d.page_count, sum(len(p.get_text()) for p in d)
        d.close()
        return (t / n) if n else 0
    except Exception:                                       # noqa: BLE001
        return -1


def main():
    prev = {}
    if os.path.isfile(OUT):
        with open(OUT, encoding='utf-8') as f:
            for r in json.load(f).get("rows", []):
                if r.get("confirmed"):
                    prev[(r["course"], r["pdf"])] = r

    rows = []
    for item in bm.MANIFEST:
        if item.get("title") != "講義まとめ" or not item.get("src"):
            continue
        html = item["src"] if os.path.isabs(item["src"]) else os.path.join(SRC_BASE, item["src"])
        if not os.path.isfile(html):
            continue
        course = item["course"]
        folder = os.path.dirname(html)
        heads = [re.sub(r'<[^>]+>', '', h) for h in
                 re.findall(r'<h2[^>]*>.*?</h2>', open(html, encoding='utf-8',
                                                       errors='replace').read(), re.S)]
        have = set()
        for h in heads:
            m = re.search(r'第\s*([0-9０-９]+)\s*回', h)
            if m:
                have.add(int(m.group(1).translate(str.maketrans('０１２３４５６７８９', '0123456789'))))

        for pdf in sorted(glob.glob(os.path.join(folder, '**', '*.pdf'), recursive=True)):
            key = (course, pdf)
            if key in prev:
                rows.append(prev[key])
                continue
            cpp = page_chars(pdf)
            row = {"course": course, "pdf": pdf, "html": html,
                   "section": None, "confirmed": False}
            if cpp < MIN_CHARS_PER_PAGE:
                row["status"] = "NOT_APPLICABLE"
                row["reason"] = ("テキスト層なし(平均%.0f字/頁)" % cpp) if cpp >= 0 else "読込失敗"
                rows.append(row)
                continue
            if course in MANUAL:
                # ファイル名の番号は当てにならない科目である。ただし
                # **PDF表紙の「第N回」は正本**なので、そこだけは見る。
                # 表紙が「第N章」の科目は回次ではないため回次ではないため一致せず、
                # 従来どおり人手へ回る(2026/8/24)。
                mn, mev = round_from_pdf(pdf, course, EXPECTED_LAST.get(course, 15))
                if mn is None:
                    row["status"] = "PENDING"
                    row["reason"] = "対応規則が一様でないため人手で確定する"
                    row["headline"] = mev
                    rows.append(row)
                    continue
                mn += OFFSET.get(course, 0)
                row["headline"] = mev
                if mn in have:
                    row["section"] = "第%d回" % mn
                    row["status"] = "AUTO"
                    row["reason"] = "PDF表紙の番号から自動対応(要確認)"
                else:
                    row["status"] = "PENDING"
                    row["reason"] = "第%d回(PDF表紙判定)に対応する節がHTMLに無い" % mn
                rows.append(row)
                continue
            last_r = EXPECTED_LAST.get(course, 15)
            n = round_from_name(os.path.basename(pdf), last_r)
            src_kind = "ファイル名"
            evidence = None
            if n is None:
                n, evidence = round_from_pdf(pdf, course, last_r)
                src_kind = "PDF表紙"
            if n is None:
                row["status"] = "PENDING"
                row["reason"] = "ファイル名からもPDF表紙からも回次を決められない"
                row["headline"] = evidence
                rows.append(row)
                continue
            n += OFFSET.get(course, 0)
            if n in have:
                row["section"] = "第%d回" % n
                row["status"] = "AUTO"
                row["reason"] = "%sの番号から自動対応(要確認)" % src_kind
                if evidence:
                    row["headline"] = evidence
            else:
                row["status"] = "PENDING"
                row["reason"] = "第%d回(%s判定)に対応する節がHTMLに無い" % (n, src_kind)
                if evidence:
                    row["headline"] = evidence
            rows.append(row)

    data = {"_readme": [
        "網羅性検査の対象表。status の意味:",
        "  AUTO           = ファイル名から自動対応。**人手で確認し confirmed:true にする**",
        "  PENDING        = 自動で決められない。人手で section を書く",
        "  CONFIRMED      = 人手で確定済み(confirmed:true で保持される)",
        "  NOT_APPLICABLE = テキスト層が無く見出しを抽出できない。MISS集計から除外",
        "confirmed:true の行は再生成しても上書きされない。",
    ], "_updated": "2026-08-23", "rows": rows}
    atomicio.write_json(OUT, data, indent=1)

    from collections import Counter
    c = Counter(r["status"] for r in rows)
    print("生成 %d 行 -> %s" % (len(rows), OUT))
    for k in ("AUTO", "PENDING", "NOT_APPLICABLE", "CONFIRMED"):
        if c.get(k):
            print("  %-16s %d" % (k, c[k]))


if __name__ == "__main__":
    main()
