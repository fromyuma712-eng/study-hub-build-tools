# -*- coding: utf-8 -*-
"""
講義まとめHTMLの「密度」と「構造」を機械的に検査する。

目的: 執筆モデル(Opus/Sonnet/Haiku)に依らず同水準の成果を保証する。
      人間/上位モデルの目視判断に頼っていた品質チェックをコード側へ移す。

使い方:
    python -X utf8 check_notes.py                # 全科目を検査
    python -X utf8 check_notes.py 科目名          # 科目名の部分一致で絞り込み
    python -X utf8 check_notes.py --calibrate    # 現状の分布を出力(閾値見直し用)

判定は「失格(FAIL)」と「注意(WARN)」の2段階。
FAILが1つでもあれば exit code 1 を返すので、追記作業の完了条件に使える。

--- 2026/8/23 改修 (独立監査の指摘に対応) ---
本検査器は「分量」しか見ておらず、次を素通ししていた。実例として、ある科目の
第9回は節がまるごと講義と無関係(PDFは組織コミットメント、HTMLは組織文化と
組織学習)であったが FAIL 0 を通過した。今回そのうち機械化できるものを追加した。

  追加: 回次の重複 / 回次の欠番 / 複数回見出し(「第4回・第5回」)の解釈 /
        HTML構造(div対応)の検証 / 全CSSクラスの定義照合 / 例外の台帳化 /
        「検査済み・例外・未検査」の内訳出力

**依然として本検査器は内容の正しさを見ない。** 節の主題が講義と一致するかは
`evidence/content-traceability/<科目>.md` の根拠対応表で担保する。
"""
import unicodedata
import datetime
import importlib.util
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))
# 講義資料の場所は site_config.py（非公開）が決める
from siteconf import C  # noqa: E402
SRC_BASE = C.SRC_BASE

# --- 閾値(既存Opus執筆分の実測分布に基づく。--calibrate で分布を確認できる) ---
MIN_ITEMS = 8            # 1セクションあたりの項目数の下限
MIN_MEAN_CHARS = 120     # 項目の平均文字数の下限(これが密度の実体)
MIN_ITEM_CHARS = 45      # 個々の項目の文字数の下限(スカスカな一行項目を弾く)
WARN_MEAN_CHARS = 150    # これを下回ると注意(Opus水準の下端)

# 数式中心の回は散文が短くなるのが正常なため閾値を緩める
FORMULA_MIN_ITEMS = 6
FORMULA_MIN_MEAN = 85

# 例外は本ファイルに定数で埋めず、理由・出所・日付つきの台帳に置く。
with open(os.path.join(ROOT, "exceptions.json"), "r", encoding="utf-8") as f:
    EX = json.load(f)

VALID_SOURCES = {"本人申告", "機械確認", "ページ内記載", "記録なし"}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


DISPOSITIONS = {"covered_by_unnumbered", "source_missing",
                "not_recorded", "numbering_offset", "unexplained"}


def validate_exceptions(ex):
    """台帳のスキーマを起動時に検証する。

    台帳は検査を免除する強い権限を持つ。必須項目を欠いた行が黙って通ると、
    「理由の書かれていない除外」が検査を素通りする(2026/8/23 指摘)。
    """
    errs = []

    # 台帳が壊れているとき、例外で落ちるのではなく FAIL 一覧として返す(2026/8/23 指摘)
    if not isinstance(ex, dict):
        return ["exceptions.json のトップレベルが辞書でない"]
    for key in ("exempt_courses", "dynamic_apps", "expected_last_round", "missing_rounds"):
        if key not in ex:
            errs.append("トップレベルのキー '%s' が無い" % key)
        elif not isinstance(ex[key], dict):
            errs.append("'%s' が辞書でない" % key)
    if errs:
        return errs

    def need(d, where):
        if not isinstance(d, dict):
            errs.append("%s: エントリが辞書でない(%s)" % (where, type(d).__name__))
            return
        for k in ("reason", "source", "date"):
            if not d.get(k):
                errs.append("%s: '%s' が空または欠落" % (where, k))
        if d.get("source") and d["source"] not in VALID_SOURCES:
            errs.append("%s: source '%s' は許容値外 (%s)"
                        % (where, d["source"], "/".join(sorted(VALID_SOURCES))))
        if d.get("date"):
            # 書式(YYYY-MM-DD)を先に確認し、その後に暦日として妥当かを見る。
            # fromisoformat だけでは "20260823" のような別書式も通る(2026/8/23 指摘)。
            if not DATE_RE.fullmatch(str(d["date"])):
                errs.append("%s: date '%s' が YYYY-MM-DD 形式でない" % (where, d["date"]))
            else:
                try:
                    datetime.date.fromisoformat(str(d["date"]))
                except ValueError:
                    errs.append("%s: date '%s' が実在する日付でない" % (where, d["date"]))

    for grp in ("exempt_courses", "dynamic_apps"):
        for k, v in ex.get(grp, {}).items():
            if not k.startswith("_"):
                need(v, "%s.%s" % (grp, k))

    last = {}
    for k, v in ex.get("expected_last_round", {}).items():
        if k.startswith("_"):
            continue
        need(v, "expected_last_round.%s" % k)
        if type(v.get("value")) is not int or v["value"] < 1:
            errs.append("expected_last_round.%s: value が正の整数でない" % k)
        else:
            last[k] = v["value"]
            # 学期進行中の科目は held_through(実施済みの最終回)までを欠番検査の対象にする。
            # 完結した科目では書かない。書き忘れて残すと未執筆の回を隠すため、範囲を厳しく縛る。
            if "held_through" in v:
                h = v["held_through"]
                if type(h) is not int or not 1 <= h <= v["value"]:
                    errs.append("expected_last_round.%s: held_through は 1〜value(%d) の整数でなければならない"
                                % (k, v["value"]))

    for k, rows in ex.get("missing_rounds", {}).items():
        if k.startswith("_"):
            continue
        if not isinstance(rows, list):
            errs.append("missing_rounds.%s: 値が配列でない(%s)" % (k, type(rows).__name__))
            continue
        if k not in last:
            errs.append("missing_rounds.%s: expected_last_round に登録が無い"
                        "(欠番免除の根拠が定まらない)" % k)
        seen_r = set()
        for i, r in enumerate(rows):
            where = "missing_rounds.%s[%d]" % (k, i)
            need(r, where)
            n = r.get("round")
            if type(n) is not int or n < 1:
                errs.append("%s: round が正の整数でない" % where)
                continue
            if n in seen_r:
                errs.append("%s: 第%d回が重複して登録されている" % (where, n))
            seen_r.add(n)
            if k in last and n > last[k]:
                errs.append("%s: 第%d回は想定最終回(第%d回)を超えている"
                            % (where, n, last[k]))
            # covered_by の要否は disposition で決める。理由文の単語から
            # 判定すると、フィールドを消すだけで検査を回避できる(2026/8/24 指摘)。
            disp = r.get("disposition")
            if disp not in DISPOSITIONS:
                errs.append("%s: disposition が未指定または不正(%r)。許容: %s"
                            % (where, disp, "/".join(sorted(DISPOSITIONS))))
            cb = r.get("covered_by")
            if disp == "covered_by_unnumbered":
                if cb is None:
                    errs.append("%s: disposition=covered_by_unnumbered には "
                                "covered_by が必須である" % where)
            elif disp in DISPOSITIONS and cb is not None:
                errs.append("%s: disposition=%s では covered_by を持てない"
                            % (where, disp))
            if cb is not None:
                if not isinstance(cb, list) or not cb:
                    errs.append("%s: covered_by は非空の配列でなければならない" % where)
                elif not all(isinstance(x, str) and x.strip() for x in cb):
                    errs.append("%s: covered_by の要素は非空の文字列でなければならない" % where)
    return errs


_ex_errs = validate_exceptions(EX)
if _ex_errs:
    print("exceptions.json のスキーマ違反:")
    for e in _ex_errs:
        print("  [FAIL] " + e)
    sys.exit(1)
EXEMPT_COURSES = set(k for k in EX["exempt_courses"] if not k.startswith("_"))
DYNAMIC_APPS = set(k for k in EX["dynamic_apps"] if not k.startswith("_"))
EXPECTED_LAST = {k: v["value"] for k, v in EX["expected_last_round"].items() if not k.startswith("_")}
HELD_THROUGH = {k: v["held_through"] for k, v in EX["expected_last_round"].items()
                if not k.startswith("_") and "held_through" in v}
MISSING_ROUNDS = {k: set(x["round"] for x in v)
                  for k, v in EX["missing_rounds"].items() if not k.startswith("_")}
# 「無番号節が第N回に相当」という台帳の主張を検証するための対応表。
# 主張を書くだけで検査しなければ、根拠のない除外を素通りさせる(2026/8/23 指摘)。
COVERED_BY = {k: {x["round"]: x["covered_by"] for x in v
                  if x.get("disposition") == "covered_by_unnumbered"}
              for k, v in EX["missing_rounds"].items() if not k.startswith("_")}

# 「第N回（第M章）」のように回と章を併記する科目がある。
# 回次として数えるのは「回」のみ。回の表記が無い科目に限り「章」で代用する。
KAI_RE = re.compile(r'第\s*([0-9０-９]+)\s*回')
SHO_RE = re.compile(r'第\s*([0-9０-９]+)\s*章')
# 見出しの回次は算用数字（半角・全角）で書く規約とする。漢数字を黙って
# 受理すると「第十五回」が存在するのに第15回が欠番と誤判定される(2026/8/23 指摘)。
# 対応表を増やすより規約違反として弾くほうが、表記が一つに定まる。
KANJI_RE = re.compile(r'第\s*[一二三四五六七八九十百]+\s*[回章]')


def rounds_in(head):
    """見出しから回次を全て取り出す。「第4回・第5回」は両方を返す。"""
    hits = KAI_RE.findall(head)
    if not hits:
        hits = SHO_RE.findall(head)
    return [to_int(x) for x in hits]


def norm_head(h):
    """見出しの突合用正規化。全角半角と前後空白の揺れだけを吸収する。"""
    return unicodedata.normalize("NFKC", h).strip()

spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
buildmod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(buildmod)

VOID = {"br", "hr", "img", "input", "meta", "link", "source", "col", "area", "base", "wbr"}


def to_int(s):
    return int(s.translate(str.maketrans('０１２３４５６７８９', '0123456789')))


class DocParser(HTMLParser):
    """本文を構文解析し、節・項目・使用クラス・div対応の破れを集める。

    正規表現ではなくパーサを使う。div の対応が崩れていても正規表現は気づかず、
    実際にある科目で1つ閉じ忘れたまま検査を通過した事故がある(2026/8/23)。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_style = self.in_script = False
        self.style_text = []       # 全ての <style> の中身(1つ目だけ見ると誤判定する)
        self.script_srcs = []      # <script src="..."> の一覧
        self.script_text = []      # インラインscriptの中身(MathJax設定の検出用)
        self.body_text = []        # style/script を除いた本文テキスト(数式検査用)
        self.stack = []            # 開いている要素 (tag, 深さ情報)
        self.sections = []         # [{"head":.., "items":[..], "formula":n}]
        self.cur = None
        self.h2_buf = None
        self.item = None           # 収集中の項目 (テキスト片, 開始深さ)
        self.classes = set()
        self.bare_h3 = False
        self.unclosed = []         # 閉じられなかったタグ
        self.stray_close = []      # 対応する開始のない終了タグ

    # --- 補助 ---
    def _new_section(self, head):
        self.cur = {"head": head, "items": [], "formula": 0}
        self.sections.append(self.cur)

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "style":
            self.in_style = True
        if tag == "script":
            self.in_script = True
            if d.get("src"):
                self.script_srcs.append(d["src"])
        if tag not in VOID:
            self.stack.append(tag)
        if self.in_style or self.in_script:
            return

        cls = (d.get("class") or "").split()
        for c in cls:
            self.classes.add(c)

        if tag == "h2":
            self.h2_buf = []
        elif tag == "h3" and "class" not in d:
            self.bare_h3 = True
        elif tag == "div" and self.item is None and any(c in ("pt", "ex") for c in cls):
            # 項目の開始。閉じるまでの深さを覚えておく(ネストしたdivも1項目に含める)
            self.item = ([], len(self.stack))
        if "formula" in cls and self.cur:
            self.cur["formula"] += 1

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "script":
            self.in_script = False
        if tag in VOID:
            return
        if tag in self.stack:
            # 直近の同名タグまで巻き戻す。間に閉じ忘れがあれば記録する
            while self.stack and self.stack[-1] != tag:
                self.unclosed.append(self.stack.pop())
            if self.stack:
                self.stack.pop()
        else:
            self.stray_close.append(tag)

        if self.in_style or self.in_script:
            return
        if tag == "h2" and self.h2_buf is not None:
            self._new_section("".join(self.h2_buf).strip())
            self.h2_buf = None
        elif tag == "div" and self.item is not None and len(self.stack) < self.item[1]:
            if self.cur is not None:
                self.cur["items"].append("".join(self.item[0]).strip())
            self.item = None

    def handle_data(self, data):
        if self.in_style:
            self.style_text.append(data)
            return
        if self.in_script:
            self.script_text.append(data)
            return
        self.body_text.append(data)
        if self.h2_buf is not None:
            self.h2_buf.append(data)
        if self.item is not None:
            self.item[0].append(data)


def check_file(course, src):
    with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    problems = []
    rows = []

    p = DocParser()
    try:
        p.feed(content)
        p.close()
    except Exception as e:                       # noqa: BLE001
        return [], [("FAIL", "(全体)", "HTMLの構文解析に失敗: %s" % e)]

    # --- HTML構造の破れ ---
    if p.unclosed:
        problems.append(("FAIL", "(全体)", "閉じられていないタグ: %s" % ", ".join(sorted(set(p.unclosed))[:5])))
    if p.stray_close:
        problems.append(("FAIL", "(全体)", "対応する開始タグのない終了タグ: %s" % ", ".join(sorted(set(p.stray_close))[:5])))
    leftover = [t for t in p.stack if t not in ("html", "body")]
    if leftover:
        problems.append(("FAIL", "(全体)", "文書末で未閉鎖: %s" % ", ".join(leftover[:5])))

    # --- セクション単位の密度検査 ---
    seen = {}
    all_rounds = []
    for sec in p.sections:
        head = sec["head"]
        if KANJI_RE.search(head):
            problems.append(("FAIL", head[:34],
                             "回次が漢数字で書かれている(算用数字で書くこと)"))
        nums = rounds_in(head)   # 「第4回・第5回」は両方、「第N回（第M章）」は回のみ
        if not nums:
            continue
        for n in nums:
            all_rounds.append(n)
            if n in seen:
                problems.append(("FAIL", head[:34], "第%d回が重複している(既出: %s)" % (n, seen[n][:24])))
            else:
                seen[n] = head
        its = sec["items"]
        cnt = len(its)
        lens = [len(t) for t in its]
        mean = sum(lens) / cnt if cnt else 0
        rows.append((head, cnt, mean, min(lens) if lens else 0))

        formula_heavy = sec["formula"] >= 3
        min_items = FORMULA_MIN_ITEMS if formula_heavy else MIN_ITEMS
        min_mean = FORMULA_MIN_MEAN if formula_heavy else MIN_MEAN_CHARS

        if cnt < min_items:
            problems.append(("FAIL", head, "項目数 %d < %d" % (cnt, min_items)))
        if cnt and mean < min_mean:
            problems.append(("FAIL", head, "平均文字数 %.0f < %d (要約が浅い)" % (mean, min_mean)))
        elif cnt and not formula_heavy and mean < WARN_MEAN_CHARS:
            problems.append(("WARN", head, "平均文字数 %.0f (目安 %d 以上)" % (mean, WARN_MEAN_CHARS)))
        for t, L in zip(its, lens):
            if L < MIN_ITEM_CHARS:
                problems.append(("FAIL", head, "短すぎる項目(%d字): %s" % (L, t[:30])))

    # --- 回次の並び順 ---
    if all_rounds != sorted(all_rounds):
        problems.append(("FAIL", "(全体)", "セクションの回次が昇順でない: %s" % all_rounds))

    # --- 回次の欠番(例外台帳で除外されたものを除く) ---
    # 期待最終回は台帳が正本。台帳に無い科目で max(実在回次) を上限にすると、
    # 末尾の節をまるごと削っても欠番と判定されない(2026/8/23 指摘)。
    expected = EXPECTED_LAST.get(course)
    if expected is None:
        problems.append(("FAIL", "(全体)",
                         "exceptions.json の expected_last_round に本科目の登録が無い"
                         "(欠番検査が成立しない)"))
    elif not all_rounds:
        # 回次を1つも抽出できない = 節が失われている可能性。黙って通してはならない。
        problems.append(("FAIL", "(全体)",
                         "回次を含む見出しが1件も無い(第%d回まで想定)" % expected))
    else:
        allowed = MISSING_ROUNDS.get(course, set())
        held = HELD_THROUGH.get(course, expected)
        gaps = [n for n in range(1, held + 1) if n not in seen and n not in allowed]
        if gaps:
            problems.append(("FAIL", "(全体)",
                             "回次の欠番: %s (第%d回まで%s。台帳に理由が無い)"
                             % (gaps, held, "実施済み" if held < expected else "想定")))
        ahead = [n for n in seen if held < n <= expected]
        if ahead:
            problems.append(("FAIL", "(全体)",
                             "held_through(第%d回)より後の回次がある: %s。台帳の held_through を更新すること"
                             % (held, sorted(ahead))))
        if held < expected:
            problems.append(("INFO", "(全体)",
                             "学期進行中: 第%d回まで実施済み / 全%d回" % (held, expected)))
        over = [n for n in seen if n > expected]
        if over:
            problems.append(("FAIL", "(全体)",
                             "台帳の想定最終回(第%d回)を超える回次: %s" % (expected, sorted(over))))

    # --- 無番号節の対応表の検証 ---
    # 台帳が「第N回は無番号節が相当する」と主張する場合、その見出しが
    # 実際にHTMLに存在することを確かめる。存在しなければ主張が空になる。
    # 突合は正規化後の完全一致とし、候補は**無番号の見出しに限る**。
    # 部分一致だと「計算機の歴史」が「計算機の歴史ではない」を通し、
    # 候補を絞らないと番号付き見出しが無番号節の代役として通る(2026/8/24 指摘)。
    cov = COVERED_BY.get(course, {})
    if cov:
        unnumbered = set(norm_head(sec["head"]) for sec in p.sections
                         if not rounds_in(sec["head"]))
        for rnd, wants in cov.items():
            for w in wants:
                if norm_head(w) not in unnumbered:
                    problems.append(("FAIL", "(全体)",
                                     "台帳が第%d回の相当節とする無番号見出し「%s」がHTMLに無い"
                                     % (rnd, w[:24])))

    # --- 使用CSSクラスが定義済みか(4種固定ではなく全クラスを照合) ---
    # 次の3つを踏まえる(いずれも2026/8/23に再現確認した誤判定):
    #   1. 部分文字列検索だと `.foo-bar` の定義で `.foo` を定義済みと誤認する
    #   2. CSSコメント `/* .zzz{} */` を定義と誤認する
    #   3. `<style>` が複数ある場合、1つ目しか見ないと正しい定義を未定義と誤判定する
    style = "".join(p.style_text)
    style_nc = re.sub(r'/\*.*?\*/', '', style, flags=re.S)   # コメント除去
    # 宣言ブロック `{...}` を除いたセレクタ部分からのみクラス名を採る
    selectors = re.sub(r'\{[^{}]*\}', ' ', style_nc)
    # 否定・関係擬似クラスの中身は「そのクラスを装飾する定義」ではない。
    # `:not(.zzz)` を .zzz の定義と数えると未定義クラスが通過する(2026/8/23 指摘)。
    # 実データに `:not([data-theme="light"])` があるため、括弧の中身のみを落とす。
    selectors = re.sub(r':(?:not|has|is|where)\s*\([^()]*\)', ' ', selectors)
    defined = set(re.findall(r'\.([A-Za-z_][-\w]*)', selectors))
    for cls in sorted(p.classes):
        if cls not in defined:
            problems.append(("FAIL", "(全体)", "CSSクラス .%s が未定義" % cls))
    if p.bare_h3 and not re.search(r'(^|[,{\s])h3[\s,{]', style_nc):
        problems.append(("WARN", "(全体)", "h3を使用しているがstyleにh3の定義が見当たらない"))

    # --- MathJax/KaTeX と数式表記の整合 ---
    # 単語の存在では判定しない。`const label="katex";` のような無関係な文字列で
    # エンジンありと誤認する(2026/8/23 指摘)。次のいずれかを根拠とする:
    #   1. script の src が mathjax/katex のスクリプトファイルを指している
    #   2. インライン script に実際の初期化構文がある
    # ファイル名に mathjax/katex を含むだけの任意スクリプト(例: katex-notes.js)を
    # 読込済みと数えない。既知の配布ファイル名に限定する(2026/8/23 指摘)。
    # 静的検査では「実際に読み込めたか」までは保証できない。配信後のブラウザ確認は
    # 別工程として RUNBOOK に置く。
    SRC_RE = re.compile(
        r'(?:^|/)(?:'
        r'katex(?:\.min)?\.js'
        r'|auto-render(?:\.min)?\.js'
        r'|tex-(?:chtml|svg|mml|mml-chtml)(?:-full)?\.js'
        r'|MathJax\.js'
        r')(?:[?#]|$)', re.I)
    INIT_RE = re.compile(r'window\.MathJax\s*=|MathJax\s*=\s*\{|renderMathInElement\s*\(|katex\.render')
    has_engine = (any(SRC_RE.search(s) for s in p.script_srcs)
                  or any(INIT_RE.search(t) for t in p.script_text))
    # 数式の検査対象は本文のみ。CSSの content:"$...$" やscript内の文字列を
    # 本文の数式と取り違えない(2026/8/23 指摘)。
    body_only = "".join(p.body_text)
    tex_forms = [
        (r'\$\$[^$]{2,}\$\$', 'ブロック数式 $$...$$'),
        (r'(?<!\$)\$[^$\n]{2,}\$(?!\$)', 'インライン数式 $...$'),
        (r'\\\([^)]{2,}\\\)', r'インライン数式 \(...\)'),
        (r'\\\[[^\]]{2,}\\\]', r'ブロック数式 \[...\]'),
    ]
    if not has_engine:
        for pat, label in tex_forms:
            if re.search(pat, body_only):
                problems.append(("FAIL", "(全体)",
                                 "数式エンジン未読込なのに %s を使用(生LaTeXが表示される)" % label))
                break

    return rows, problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    calibrate = '--calibrate' in sys.argv
    needle = args[0] if args else None

    n_fail = 0
    checked, exempted, skipped = [], [], []

    for item in buildmod.MANIFEST:
        if item.get("url") or item.get("dest") in DYNAMIC_APPS:
            continue
        # 密度仕様は「講義まとめ」に対してのみ定義されている。期末テスト・公式まとめ・
        # 模擬試験・ドリル等は構造が異なるため対象外とする(2026/8/20)。
        if item.get("title") != "講義まとめ":
            continue
        if needle and needle not in item["course"]:
            continue
        if item["course"] in EXEMPT_COURSES:
            exempted.append(item["course"])
            if not needle:
                continue
        src = item["src"] if os.path.isabs(item["src"]) else os.path.join(SRC_BASE, item["src"])
        if not os.path.isfile(src):
            skipped.append(item["course"])
            continue

        rows, problems = check_file(item["course"], src)
        checked.append(item["course"])

        if calibrate:
            print("\n== %s ==" % item["course"])
            for head, n, mean, mn in rows:
                print("   %-46s items=%2d  mean=%5.0f  min=%4d" % (head[:46], n, mean, mn))
            continue

        if problems:
            print("\n== %s ==" % item["course"])
            for level, head, msg in problems:
                if level == "FAIL":
                    n_fail += 1
                print("  [%s] %s / %s" % (level, head[:34], msg))

    if not calibrate:
        # FAIL:0 だけでは「全要件を満たした」根拠にならない。何件が未検査かを必ず出す。
        print("\nFAIL: %d" % n_fail)
        print("検査済み %d 科目 / 例外(未検査) %d 科目 / 原本なし %d 科目"
              % (len(checked), len([c for c in exempted if c not in checked]), len(skipped)))
        if exempted and not needle:
            print("  ※ 例外は合格ではなく未検査である: %s"
                  % "、".join(sorted(set(c for c in exempted if c not in checked))))
        print("  ※ 本検査器は内容の正しさを見ない。節の主題が講義と一致するかは"
              " evidence/content-traceability/ の根拠対応表で担保すること。")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
