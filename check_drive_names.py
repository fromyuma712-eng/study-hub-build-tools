# -*- coding: utf-8 -*-
"""ドライブの学期フォルダの資料名が、命名規則に沿っているかを調べる（既定は秋学期。--apply で改名案を実行）。

規則（2026/10/8 本人指示で制定）:
  <科目フォルダ名>_第N回.<拡張子>                … その回のスライド（1種類のとき）
  <科目フォルダ名>_第N回_<種別>[_<補足>].<拡張子>  … 種別 = スライド／配布レジュメ／講義文字起こし／練習問題／演習／演習完成例／授業中撮影 など
  <科目フォルダ名>_<名称>.<拡張子>                … 回に属さない資料（授業ルール・シラバスなど）
  ・講義の字幕・キャプション（Google ドキュメント、自動文字起こし）は「講義文字起こし」。
  ・LMS から落とした意味のない英数字名（例 351b5397280c249f.pdf）は、先頭ページで回を確かめて直す。
  ・科目フォルダの外（学期フォルダ直下）のファイルと、`調査資料` など本人の作業フォルダは対象外。

使い方:
    python -X utf8 check_drive_names.py            # 規則に沿わないものを一覧
    python -X utf8 check_drive_names.py --map FILE  # 改名案(TSV: 旧<TAB>新、フォルダからの相対)を実行する前に確認
"""
import glob
import os
import re
import sys
import unicodedata

ROOT = (glob.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/マイドライブ/01_大学/2026年度/秋学期")) or [""])[0]
SKIP_DIRS = {"調査資料", "秋学期シラバス"}
ROUND = re.compile(r"^第\d+回(_[^_]+){0,2}$")


def nfc(x):
    return unicodedata.normalize("NFC", x)


def conforming(folder, name):
    stem, _ = os.path.splitext(nfc(name))
    folder = nfc(folder)
    if not stem.startswith(folder + "_"):
        return False
    rest = stem[len(folder) + 1:]
    return bool(ROUND.match(rest)) or ("_" not in rest and rest != "" and not re.fullmatch(r"[0-9a-f]{12,}", rest) and not re.fullmatch(r"\d+", rest))


def scan(root=ROOT):
    bad = []
    for folder in sorted(os.listdir(root)):
        p = os.path.join(root, folder)
        if not os.path.isdir(p) or nfc(folder) in SKIP_DIRS:
            continue
        for dp, dns, fns in os.walk(p):
            dns[:] = [d for d in dns if nfc(d) not in SKIP_DIRS]
            for n in sorted(fns):
                if n.startswith("."):
                    continue
                if not conforming(folder, n):
                    bad.append(os.path.relpath(os.path.join(dp, n), root))
    return bad


def main():
    if not ROOT:
        sys.exit("ドライブの学期フォルダが見つかりません")
    if "--map" in sys.argv:
        m = sys.argv[sys.argv.index("--map") + 1]
        for line in open(m, encoding="utf-8"):
            old, new = line.rstrip("\n").split("\t")
            a, b = os.path.join(ROOT, old), os.path.join(ROOT, new)
            state = "OK" if os.path.exists(a) and not os.path.exists(b) else "衝突/欠落"
            print("%s  %s -> %s" % (state, old, new))
        return
    bad = scan()
    for b in bad:
        print("規則外:", b)
    print("\n規則外 %d 件" % len(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
