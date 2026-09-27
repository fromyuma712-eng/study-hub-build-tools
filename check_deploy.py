# -*- coding: utf-8 -*-
"""
study-hub 配信突合スクリプト（第三の検査器）

原本（各科目フォルダの .html）と配信物（public/**/index.html）が
一致しているかを MANIFEST 全件について照合する。

存在理由:
    2026/8/20、原本13科目を更新したまま build.py を実行しておらず、
    公開サイトに一切反映されていない状態が検出された。
    check_notes.py（密度）と check_coverage.py（網羅性）は
    いずれも原本のみを見るため、この欠落を検出できない。
    本スクリプトが「書いたものが実際に配信されたか」を担保する。

使い方:
    python -X utf8 check_deploy.py          # 全件照合
    python -X utf8 check_deploy.py --quiet  # 不一致のみ表示

終了コード:
    0 = 全件一致 / 1 = 不一致あり（未ビルド・未配置・内容相違）
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from build import MANIFEST, PUBLIC, SRC_BASE  # noqa: E402


def resolve(src):
    return src if os.path.isabs(src) else os.path.join(SRC_BASE, src)


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    quiet = "--quiet" in sys.argv
    rows, ng = [], 0

    for m in MANIFEST:
        # dir 項目（PWA のフォルダ複製）は、直下のファイルを1つずつ突き合わせる。
        # src を持たないからと飛ばすと、検査していないのに一致と表示してしまう。
        if m.get("dir"):
            sd = resolve(m["dir"])
            dd = os.path.join(PUBLIC, m["dest"].rstrip("/"))
            label = "%s / %s" % (m["course"], m["title"])
            if not os.path.isdir(sd):
                rows.append(("原本無し", label, m["dest"], "")); ng += 1
                continue
            names = sorted(n for n in os.listdir(sd) if os.path.isfile(os.path.join(sd, n)))
            bad = []
            for n in names:
                sp, dp = os.path.join(sd, n), os.path.join(dd, n)
                if not os.path.exists(dp):
                    bad.append(n + " 未配置")
                elif digest(sp) != digest(dp):
                    bad.append(n + " 不一致")
            extra = sorted(set(os.listdir(dd)) - set(names)) if os.path.isdir(dd) else []
            if bad:
                rows.append(("不一致", label, m["dest"], " / ".join(bad))); ng += 1
            elif extra:
                rows.append(("余分", label, m["dest"], "配信側に " + " ".join(extra))); ng += 1
            else:
                rows.append(("一致", label, m["dest"], "%d files" % len(names)))
            continue
        if not m.get("src"):
            continue  # 生成ページ（原本を持たない）は対象外
        s, d = resolve(m["src"]), os.path.join(PUBLIC, m["dest"])
        label = "%s / %s" % (m["course"], m["title"])

        if not os.path.exists(s):
            rows.append(("原本無し", label, m["dest"], "")); ng += 1
        elif not os.path.exists(d):
            rows.append(("未配置", label, m["dest"], "build.py 未実行")); ng += 1
        elif digest(s) != digest(d):
            delta = os.path.getsize(s) - os.path.getsize(d)
            rows.append(("不一致", label, m["dest"], "原本比 %+d bytes" % delta)); ng += 1
        else:
            rows.append(("一致", label, m["dest"], ""))

    show = [r for r in rows if r[0] != "一致"] if quiet else rows
    if show:
        print("%-8s %-42s %-22s %s" % ("状態", "科目 / 種別", "配信先", "備考"))
        print("-" * 96)
        for st, label, dest, note in sorted(show, key=lambda r: (r[0] == "一致", r[1])):
            print("%-8s %-42s %-22s %s" % (st, label[:41], dest, note))

    print("\n照合 %d 件 / 不一致 %d 件" % (len(rows), ng))
    if ng:
        print("→ 未完了。`python extract_index.py && python build.py && "
              "python generate_extra_pages.py` を実行し、再度本検査を通すこと。")
    else:
        print("→ 原本と配信物は完全に一致している。")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
