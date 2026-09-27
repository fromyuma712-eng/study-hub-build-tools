# -*- coding: utf-8 -*-
"""
分野別インデックスページ(fields/)とティア表ページ(tier/)を生成する。
headings.json(extract_index.pyの出力)を読み、本文には一切触れず
リンクのみで構成する(単一の情報源はあくまで各科目の講義まとめHTML)。

使い方: python generate_extra_pages.py (build.py の後に実行)
"""
import atomicio
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")

spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
buildmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(buildmod)

esc = buildmod.esc
page = buildmod.page
sect_head = buildmod.sect_head
C = buildmod.C

with open(os.path.join(ROOT, "headings.json"), "r", encoding="utf-8") as f:
    HEADINGS = json.load(f)

# 科目名 -> 分野タグ・分野の並び・ティア表は個人データなので site_config.py（非公開）に置く
COURSE_TAGS = C.COURSE_TAGS
FIELD_ORDER = C.FIELD_ORDER
TIER_DATA = C.TIER_DATA


def build_fields_page():
    by_field = {k: [] for k in FIELD_ORDER}
    for entry in HEADINGS:
        tags = COURSE_TAGS.get(entry["course"], ["未分類"])
        for tag in tags:
            by_field.setdefault(tag, [])
            for h in entry["headings"]:
                by_field[tag].append((entry["course"], entry["dest"], h["anchor"], h["text"]))

    parts = ["<section class=\"sect\"><div class=\"body\"><p class=\"note\">科目をまたいで、各分野で何を扱ったかを一覧できる。"
             "行を押すと該当科目のページの該当箇所へ入る（本文はここに複製していない）。</p></div></section>"]
    first = True
    for field in FIELD_ORDER:
        rows = by_field.get(field, [])
        if not rows:
            continue
        n_courses = len({r[0] for r in rows})
        sid = "f-%d" % FIELD_ORDER.index(field)
        parts.append("<details class=\"sect\" id=\"" + sid + "\"" + (" open" if first else "") + "><summary>"
                     + sect_head("FIELD", field, "%d COURSES ∧ %d ITEMS" % (n_courses, len(rows)), chevron=True)
                     + "</summary><div class=\"body\"><div class=\"rows\">")
        first = False
        for course, dest, anchor, text in rows:
            parts.append(
                "<a class=\"row rise\" href=\"../" + dest + "#" + anchor + "\">"
                "<span class=\"rc\">" + esc(course) + "</span>"
                "<span class=\"rt\">" + esc(text) + "</span></a>")
        parts.append("</div></div></details>")

    spec = ("<span class=\"sp\"><b>" + str(len(HEADINGS)) + "</b> COURSES INDEXED</span><span class=\"sp\"><b>"
            + str(sum(1 for f in FIELD_ORDER if by_field.get(f))) + "</b> FIELDS</span>")
    out_dir = os.path.join(PUBLIC, "fields")
    os.makedirs(out_dir, exist_ok=True)
    atomicio.write_text(os.path.join(out_dir, "index.html"), page("".join(parts), spec, face="fields"))
    print("fields page -> public/fields/index.html")





def build_tier_page():
    parts = ["<section class=\"sect\"><div class=\"body\">" + "".join(
        "<p class=\"note\">" + p + "</p>" for p in C.TIER_INTRO) + "</div></section>"]
    for tier, desc, items in TIER_DATA:
        # 色で段を分けない（燠火以外の色を持ち込まない）。注意を引く「要確認」だけ燠火で示す。
        warn = tier == "要確認"
        label = ("TIER " + tier) if len(tier) == 1 else ("CHECK" if warn else "OTHER")
        name = tier + " — " + desc
        parts.append("<details class=\"sect" + (" warn" if warn else "") + "\" id=\"t-" + esc(tier) + "\" open><summary>"
                     + sect_head(label, name, "%d COURSES" % len(items), chevron=True)
                     + "</summary><div class=\"body\"><div class=\"grid\">")
        for course, comment in items:
            parts.append(
                "<div class=\"card rise\">"
                "<span class=\"bl\"></span><span class=\"br\"></span>"
                "<div class=\"crs\">" + esc(course) + "</div>"
                "<div class=\"dsc\">" + esc(comment).replace("**", "") + "</div>"
                "</div>"
            )
        parts.append("</div></div></details>")

    spec = ("<span class=\"sp\">暫定評価</span><span class=\"sp\"><b>" + str(sum(len(x[2]) for x in TIER_DATA))
            + "</b> COURSES</span><span class=\"sp\">随時更新</span>")
    out_dir = os.path.join(PUBLIC, "tier")
    os.makedirs(out_dir, exist_ok=True)
    atomicio.write_text(os.path.join(out_dir, "index.html"), page("".join(parts), spec, face="tier"))
    print("tier page -> public/tier/index.html")


if __name__ == "__main__":
    build_fields_page()
    build_tier_page()
