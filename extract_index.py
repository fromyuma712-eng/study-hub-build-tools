# -*- coding: utf-8 -*-
"""
既存の講義まとめHTML群からh2見出しを一括抽出し、
1) 各h2にアンカーID(id="s1","s2"...)を機械的に付与(本文は読まない・変更しない)
2) 見出し一覧をJSONに書き出す(分野インデックスページ生成の元データ)

本文を人間が読み直す必要がないよう、正規表現のみで処理する。
"""
import atomicio
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
# 講義資料の場所は site_config.py（非公開）が決める
from siteconf import C  # noqa: E402
SRC_BASE = C.SRC_BASE

# build.pyのMANIFESTと同じ対応(src相対パス, 科目名, code, dest)
# ここではsrcパスとdestパスのみ機械的に読み込む
import importlib.util
spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
buildmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(buildmod)

H2_RE = re.compile(r'<h2(?:\s+id="[^"]*")?>(.*?)</h2>', re.DOTALL)

def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s).strip()

results = []  # [{course, code, dest, headings:[{text, anchor}]}]

# 問題集などのJS動的レンダリングのアプリ(h2がテンプレートリテラル内)のため索引対象から除外
DYNAMIC_APPS = set(C.DYNAMIC_APPS)

for item in buildmod.MANIFEST:
    # url(外部リンク)と dir(フォルダごと複製するアプリ)は講義まとめではないため索引対象外
    if item.get("url") or "src" not in item:
        continue
    if item["dest"] in DYNAMIC_APPS:
        continue
    src = os.path.join(SRC_BASE, item["src"])
    if not os.path.isfile(src):
        continue
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    headings = []
    counter = [0]

    def repl(m):
        counter[0] += 1
        anchor = "s%d" % counter[0]
        text = strip_tags(m.group(1))
        # 既にid属性があれば維持し、その実際のidを索引へ入れる（連番を入れると、idを付け替えた頁でリンクが壊れる＝2026/10/8修正）
        mid = re.search(r'<h2[^>]*\sid="([^"]+)"', m.group(0))
        headings.append({"text": text, "anchor": mid.group(1) if mid else anchor})
        if mid:
            return m.group(0)
        return '<h2 id="%s">%s</h2>' % (anchor, m.group(1))

    new_content = H2_RE.sub(repl, content)

    if new_content != content:
        atomicio.write_text(src, new_content)

    results.append({
        "course": item["course"],
        "code": item["code"],
        "title": item["title"],
        "dest": item["dest"].replace("/index.html", "/"),
        "headings": headings,
    })

atomicio.write_json(os.path.join(ROOT, "headings.json"), results)

total_h2 = sum(len(r["headings"]) for r in results)
print("processed %d files, %d headings total" % (len(results), total_h2))
for r in results:
    print("  %s: %d headings" % (r["course"], len(r["headings"])))
