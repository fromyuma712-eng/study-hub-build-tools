# -*- coding: utf-8 -*-
"""
各科目の「配布資料の実主題」と「HTMLの節見出し」を並べた対照表を生成する。

根拠対応表(evidence/content-traceability/)を作る際の一次資料。

**なぜこの形式か**
内容の誤りを機械判定しようとして2度失敗した(2026/8/23)。
  1. 本文の文字2-gram照合 … 資料が17万字規模だと日本語はほぼ何でも一致し無意味
  2. 見出し語の語幹照合   … 真の欠陥(0〜50%)と偽陽性(0〜100%)の分布が重なり閾値を引けない
実際に3件の欠陥(3科目)を見つけたのは、
**PDFの実主題とHTML節見出しを人が突き合わせる**方法だった。機械には
「材料を並べるところまで」をさせ、判定は人が行う。

主題の抽出は各ページの最大フォント行による。PDFを画像として読む必要がなく
ほぼ無償である(RUNBOOK §8)。

使い方:
    python -X utf8 gen_source_topics.py
    -> evidence/source-topics/<科目>.md
"""
import atomicio
import glob
import importlib.util
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import fitz  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
# 講義資料の場所は site_config.py（非公開）が決める
from siteconf import C  # noqa: E402
SRC_BASE = C.SRC_BASE
OUT = os.path.join(ROOT, "evidence", "source-topics")

_s = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
buildmod = importlib.util.module_from_spec(_s)
_s.loader.exec_module(buildmod)


def topics(path, cap=16):
    """各ページの最大フォント行を主題候補として返す"""
    try:
        doc = fitz.open(path)
    except Exception:                                       # noqa: BLE001
        return None, 0, 0
    out, chars = [], 0
    for page in list(doc)[:cap]:
        chars += len(page.get_text())
        best = (0, "")
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                t = "".join(sp["text"] for sp in line["spans"]).strip()
                if not t:
                    continue
                size = max(sp["size"] for sp in line["spans"])
                if size > best[0]:
                    best = (size, t)
        h = re.sub(r'\s+', ' ', best[1])[:44]
        if h and (not out or out[-1] != h):
            out.append(h)
    n = doc.page_count
    doc.close()
    return out, n, chars


def main():
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for item in buildmod.MANIFEST:
        if item.get("title") != "講義まとめ" or not item.get("src"):
            continue
        src = item["src"] if os.path.isabs(item["src"]) else os.path.join(SRC_BASE, item["src"])
        if not os.path.isfile(src):
            continue
        folder = os.path.dirname(src)
        html = open(src, encoding='utf-8', errors='replace').read()
        heads = [re.sub(r'<[^>]+>', '', h).strip()
                 for h in re.findall(r'<h2[^>]*>.*?</h2>', html, re.S)]

        lines = ['# %s — 資料の実主題とHTML節の対照' % item["course"], '',
                 '機械生成。**判定は人が行うこと。**', '',
                 '## HTMLの節（%d件）' % len(heads), '']
        lines += ['%2d. %s' % (i, h) for i, h in enumerate(heads, 1)]
        lines += ['', '## 配布資料の実主題（各ページの最大フォント行）', '',
                  '冒頭の「問1」「前回の復習」等は**前回分の演習**であり主題ではない。',
                  '画像PDFは抽出できないため「テキスト層なし」と記す。', '',
                  '| 資料 | 頁 | 抽出した主題 |', '|---|--:|---|']
        for f in sorted(glob.glob(os.path.join(folder, '**', '*.pdf'), recursive=True)):
            ts, n, chars = topics(f)
            name = os.path.relpath(f, folder).replace(os.sep, '/')
            if ts is None:
                lines.append('| %s | — | 読込失敗 |' % name)
            elif n and chars / min(n, 16) < 50:
                lines.append('| %s | %d | **テキスト層なし（画像PDF）** |' % (name, n))
            else:
                lines.append('| %s | %d | %s |' % (name, n, ' / '.join(ts[:8])))
        txts = sorted(glob.glob(os.path.join(folder, '**', '*.txt'), recursive=True))
        if txts:
            lines += ['', '## 講義音声の書き起こし（PDFに無くてもここにあれば資料内）', '']
            for f in txts:
                lines.append('- `%s`（%s KB）'
                             % (os.path.relpath(f, folder).replace(os.sep, '/'),
                                format(os.path.getsize(f) // 1024, ',')))
        dst = os.path.join(OUT, re.sub(r'[\/:*?"<>|]', '_', item["course"]) + '.md')
        atomicio.write_text(dst, '\n'.join(lines))
        made += 1
        print('  %s' % os.path.basename(dst))
    print('\n生成 %d 科目 -> %s' % (made, OUT))


if __name__ == "__main__":
    main()
