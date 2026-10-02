# -*- coding: utf-8 -*-
"""
PDFのスライド見出しが、講義まとめHTMLの該当セクションに反映されているかを機械検査する。

check_notes.py が「密度」を見るのに対し、こちらは「網羅性」を見る。
執筆モデルが取りこぼした見出しは執筆モデル自身には見えないため、
自己申告ではなくコード側で検出する必要がある。

使い方:
    python check_coverage.py <PDFパス> <HTMLパス> <見出しに含まれる文字列>

例:
    python -X utf8 check_coverage.py ^
      "<資料フォルダ>\\<学期>\\<科目>\\<資料>_4.pdf" ^
      "<資料フォルダ>\\<学期>\\<科目>\\講義まとめ.html" ^
      "第4回"

第3引数は <h2> 見出しの一部（"第4回" "第9章" など）。その見出しのセクション本文と、
PDFから抽出した各スライド見出しを照合する。

判定は文字2-gramの重なり率。表記ゆれ（全角半角・送り仮名）に強く、
完全一致を要求しないため誤検出が少ない。
"""
import json
import os
import re
import sys
import unicodedata

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF(fitz) が必要です: pip install pymupdf")

# 見出しとみなす条件
MIN_TITLE_LEN = 4          # これ未満は見出し扱いしない
MAX_TITLE_LEN = 60         # これ超は本文とみなす
FONT_RATIO = 0.92          # ページ内最大フォントのこの割合以上を見出し候補とする
# 一致率の判定帯。表記を変えて要約すると一致率は下がるため、
# 中間帯は「未反映」と断定せず目視確認に回す（誤検出で作業を止めないため）
MISS_THRESHOLD = 0.45      # これ未満は未反映とみなす（FAIL）
CHECK_THRESHOLD = 0.62     # これ未満は要確認（WARN）

# 見出しとして無意味な定型句
SKIP_PAT = re.compile(r'^(出典|参考|注|補足|参考文献|Appendix|目次|まとめ|ご参考)', re.I)
# 見出しではない定型行。全採用にしたことでページ番号・資料番号・
# ヘッダフッタが混入するようになったため除外する(2026/8/23)。
NOISE_PAT = re.compile(
    r'^([0-9]+|[0-9]+\s*[-/]\s*[0-9]+'          # 1 / 15-1
    r'|.{0,12}[0-9]+\s*[-]\s*[0-9]+'            # 組織論15-1
    r'|.{0,10}資料\s*[0-9]+'                     # 組織論 資料15
    r'|.{0,10}第\s*[0-9]+\s*[回章]?\s*'         # 例: 「科目名 第15回」
    r'|https?://\S+'                             # URLだけの行（参考資料の一覧）(2026/9/30)
    r'|[ぁ-ん]{1,4}。)$')                        # 折り返された文の末尾「ださい。」(2026/9/30)
# 数式だけの行（スライドの数式を文字に起こしたもの）。講義まとめは同じ式を MathJax の記法で書くため、
# 文字の一致で照合できない。数学用英数字（U+1D400〜）・定義記号≔・所属∈・サイコロの目（U+2680〜）を含む行は見出しとしない(2026/10/2)
FORMULA_PAT = re.compile(r'[\U0001D400-\U0001D7FF≔∈⚀-⚅]')


def norm(s):
    """比較用に正規化: 全半角統一・空白/記号除去"""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r'[\s\u3000（）()「」『』【】、。，．・:：;；/／\-—–~〜]', '', s)
    return s


def bigrams(s):
    s = norm(s)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


_COURSE_BOILER = None


def learn_boilerplate(pdfs, ratio=0.5):
    """科目内の半数以上のPDFに現れる行を定型文として学習する"""
    global _COURSE_BOILER
    _COURSE_BOILER = None
    seen = {}
    for f in pdfs:
        for t in set(norm(x) for x in pdf_headings(f)):
            seen[t] = seen.get(t, 0) + 1
    need = max(2, int(len(pdfs) * ratio))
    _COURSE_BOILER = {t for t, c in seen.items() if c >= need}
    return _COURSE_BOILER


def pdf_headings(path):
    """各ページの最大フォント行を見出しとして抽出"""
    doc = fitz.open(path)
    out = []
    for page in doc:
        spans = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                text = "".join(sp["text"] for sp in line["spans"]).strip()
                if not text:
                    continue
                size = max(sp["size"] for sp in line["spans"])
                spans.append((size, text))
        if not spans:
            continue
        top = max(s for s, _ in spans)
        for size, text in spans:
            if size < top * FONT_RATIO:
                continue
            if not (MIN_TITLE_LEN <= len(text) <= MAX_TITLE_LEN):
                continue
            if SKIP_PAT.match(text) or NOISE_PAT.match(text.strip()) or FORMULA_PAT.search(text):
                continue
            out.append(text)
            # 2026/8/23 利用者決定: `break` を外し FONT_RATIO 内の行を全採用する。
            # 1ページ1見出しでは、1ページに複数スライドを載せた配布資料
            # (実測 536件中176件・33%) で見出しを取りこぼしていた。
    npages = doc.page_count
    doc.close()

    # 走るヘッダ・定型文の除去。見出しを全採用にしたことで
    # 「授業計画（後半）」「本日の講義内容」等が毎ページ混入するようになった
    # (2026/8/23)。同一PDF内で多くのページに現れる行は見出しではない。
    from collections import Counter
    freq = Counter(norm(t) for t in out)
    limit = max(2, int(npages * 0.34))
    out = [t for t in out if freq[norm(t)] <= limit]

    # 科目内の他PDFにも現れる行は定型文（デッキ共通のヘッダ・目次）である。
    # 同一PDF内では1回ずつしか出ないため、上の頻度フィルタでは落ちない。
    if _COURSE_BOILER is not None:
        out = [t for t in out if norm(t) not in _COURSE_BOILER]

    # 連続重複を除去（同じ見出しが複数ページに跨るスライド）
    dedup = []
    for t in out:
        if not dedup or norm(t) != norm(dedup[-1]):
            dedup.append(t)
    return dedup


def section_text(html_path, needle):
    """指定した見出しを含む <h2> セクションの本文テキストを返す"""
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
    parts = re.split(r'<h2(?:\s+id="[^"]*")?>(.*?)</h2>', content, flags=re.DOTALL)
    for i in range(1, len(parts) - 1, 2):
        head = re.sub(r'<[^>]+>', '', parts[i])
        if needle in head:
            body = re.sub(r'<[^>]+>', ' ', parts[i + 1])
            return head.strip(), body
    return None, None


def scan_all(needle=None):
    """MANIFEST全件を走査する。対応表は coverage_manifest.json が正本。

    2026/8/23 利用者決定:
      - 毎回すべて走査する(走査はローカルCPUのみでトークンを消費しない)
      - MISS 0 を必須。ただし画像PDF等は NOT_APPLICABLE として別集計
    """
    import importlib.util
    root = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("bm", os.path.join(root, "build.py"))
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    cmpath = os.path.join(root, "coverage_manifest.json")
    if not os.path.isfile(cmpath):
        print("coverage_manifest.json がありません。先に gen_coverage_manifest.py を実行してください。")
        return 2
    with open(cmpath, encoding="utf-8") as f:
        cm = json.load(f)

    # 科目ごとに定型文を学習してから走査する
    from collections import defaultdict
    by_course = defaultdict(list)
    for r in cm["rows"]:
        if r.get("status") != "NOT_APPLICABLE" and os.path.isfile(r["pdf"]):
            by_course[r["course"]].append(r["pdf"])
    boiler = {}
    for c, fs in by_course.items():
        if needle and needle not in c:
            continue
        boiler[c] = learn_boilerplate(fs)

    n_miss = n_check = n_na = n_ok = 0
    cur_course = None
    for row in cm["rows"]:
        if needle and needle not in row["course"]:
            continue
        if row.get("status") == "NOT_APPLICABLE":
            n_na += 1
            continue
        global _COURSE_BOILER
        if row["course"] != cur_course:
            cur_course = row["course"]
            _COURSE_BOILER = boiler.get(cur_course, set())
        pdf, html, sec = row["pdf"], row["html"], row["section"]
        if not (os.path.isfile(pdf) and os.path.isfile(html)):
            print("  [欠落] %s %s" % (row["course"], sec)); n_miss += 1
            continue
        head, body = section_text(html, sec)
        if body is None:
            print("  [節なし] %s %s" % (row["course"], sec)); n_miss += 1
            continue
        bbg = bigrams(body)
        miss = []
        chk = 0
        for t in pdf_headings(pdf):
            bg = bigrams(t)
            if not bg:
                continue
            r = len(bg & bbg) / len(bg)
            if r < MISS_THRESHOLD:
                miss.append(t)
            elif r < CHECK_THRESHOLD:
                chk += 1
        if miss:
            print("  [MISS %2d] %-22s %-14s %s" % (len(miss), row["course"][:22], sec,
                                                   " / ".join(m[:22] for m in miss[:3])))
            n_miss += len(miss)
        else:
            n_ok += 1
        n_check += chk

    print("\n節 OK %d / MISS %d / CHECK %d / 対象外(NOT_APPLICABLE) %d"
          % (n_ok, n_miss, n_check, n_na))
    print("  ※ CHECK は表現を変えて反映済みか目視確認する対象。FAIL には数えない。")
    return 1 if n_miss else 0


def main():
    if "--all" in sys.argv:
        rest = [a for a in sys.argv[1:] if not a.startswith("--")]
        return scan_all(rest[0] if rest else None)
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    pdf, html, needle = sys.argv[1], sys.argv[2], sys.argv[3]
    for p in (pdf, html):
        if not os.path.isfile(p):
            sys.exit("見つかりません: %s" % p)

    head, body = section_text(html, needle)
    if body is None:
        sys.exit('HTMLに "%s" を含む <h2> がありません。先にセクションを作成してください。' % needle)

    body_bg = bigrams(body)
    heads = pdf_headings(pdf)

    print("対象セクション: %s" % head)
    print("PDF見出し %d 件を照合\n" % len(heads))

    missing, check = [], []
    for t in heads:
        bg = bigrams(t)
        if not bg:
            continue
        ratio = len(bg & body_bg) / len(bg)
        if ratio < MISS_THRESHOLD:
            mark = "MISS"
            missing.append(t)
        elif ratio < CHECK_THRESHOLD:
            mark = "CHECK"
            check.append(t)
        else:
            mark = "OK"
        print("  [%-5s] %4.0f%%  %s" % (mark, ratio * 100, t))

    print("\n未反映(MISS): %d 件 / 要確認(CHECK): %d 件" % (len(missing), len(check)))
    if missing:
        print("\n■ まとめに反映されていない見出し（PDFを読み直して追記すること）")
        for t in missing:
            print("   - %s" % t)
    if check:
        print("\n■ 表現を変えて反映済みか目視確認する見出し")
        for t in check:
            print("   - %s" % t)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
