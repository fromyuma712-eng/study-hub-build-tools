# -*- coding: utf-8 -*-
"""
check_notes.py の検体スイート。

**基線確認と欠陥検出試験を分けて数える。**
以前は両者を合算して「9項目の発火」と報告しており、実際の変異試験は8件だった
(2026/8/23 指摘)。基線は「壊していない検体でFAILが出ないこと」の確認であり、
欠陥を検出できたことの証拠ではない。

使い方:
    python -X utf8 test_check_notes.py
"""
import importlib.util
import io
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HUB = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('cn', os.path.join(HUB, 'check_notes.py'))
cn = importlib.util.module_from_spec(_s)
_s.loader.exec_module(cn)

# 試験に使う実在の科目・講義まとめ・資料の場所は site_config.py（非公開）が決める
from siteconf import C  # noqa: E402

# 合成検体を検査させる科目。想定最終回15で、無番号節の対応表(covered_by)を
# 持たないものを選ぶ。covered_by を持つ科目だと、合成検体に当該見出しが
# 無いため全基線がFAILになる(2026/8/23)。
SYNTH_COURSE = C.TEST_SYNTH_COURSE

_SRC_BASE = C.SRC_BASE
REAL = os.path.join(_SRC_BASE, C.TEST_REAL_NOTE)

# 合成検体の土台。実ファイルの科目として検査させるため、台帳の想定最終回(15)に合わせる。
STYLE = '.wrap{}.pt{}.block{}.small{}'
ITEM = '<div class="pt">%s</div>' % ('あ' * 200)


def doc(body, style_extra='', head_extra=''):
    return ('<html><head><style>%s%s</style>%s</head><body><div class="wrap">%s</div>'
            '</body></html>' % (STYLE, style_extra, head_extra, body))


def full_course(last=15, skip=()):
    """第1回〜last回を揃えた正常な検体"""
    out = []
    for n in range(1, last + 1):
        if n in skip:
            continue
        out.append('<h2>第%d回 — X</h2><div class="block">%s</div>' % (n, ITEM * 8))
    return ''.join(out)


def fails(source, course=SYNTH_COURSE):
    tmp = os.path.join(tempfile.gettempdir(), 'tcn.html')
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(source)
    _, probs = cn.check_file(course, tmp)
    return [m for lv, h, m in probs if lv == 'FAIL']


results = {'baseline': [], 'mutation': []}


def baseline(label, source, course=SYNTH_COURSE):
    f = fails(source, course)
    ok = not f
    results['baseline'].append(ok)
    print('  %s %-36s %s' % ('OK ' if ok else 'NG!', label, f[:1] or 'FAIL 0'))


def mutation(label, source, expect, course=SYNTH_COURSE):
    f = fails(source, course)
    hit = [m for m in f if expect in m]
    results['mutation'].append(bool(hit))
    print('  %s %-36s %s' % ('OK ' if hit else 'NG!', label,
                             (hit[0][:50] if hit else '検出できず')))


print('== 基線（壊していない検体でFAILが出ないこと）==')
with open(REAL, encoding='utf-8') as f:
    real = f.read()
baseline('実ファイル', real, course=C.TEST_REAL_COURSE)
baseline('合成・全回そろい', doc(full_course()))

print('\n== 欠陥検出（計画 §5-1 の各項目に対応）==')

# 2-1 回次重複
mutation('2-1 回次の重複',
         doc(full_course().replace('<h2>第14回', '<h2>第13回', 1)), '重複')

# 2-2 回次欠番 / 回次ゼロ
mutation('2-2 回次の欠番',
         doc(full_course(skip=(7,))), '欠番')
mutation('2-2 回次を1件も抽出できない',
         doc('<h2>導入</h2><div class="block">%s</div>' % (ITEM * 8)), '1件も無い')
mutation('2-2 想定最終回を超える回次',
         doc(full_course() + '<h2>第99回 — X</h2><div class="block">%s</div>' % (ITEM * 8)),
         '超える回次')
mutation('2-2 台帳に期待最終回の登録が無い',
         doc(full_course()), 'expected_last_round', course='未登録科目')

# 2-3 複数回見出し
mutation('2-3 「第4回・第5回」の解釈',
         doc(full_course().replace('<h2>第6回 — X</h2>', '<h2>第4回・第5回 — X</h2>', 1)),
         '重複')

# 2-5 CSSクラス
mutation('2-5 未定義CSSクラス',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60)), '.zzz が未定義')
mutation('2-5 部分文字列の衝突（.zzz-long定義で.zzz使用）',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60),
             style_extra='.zzz-long{}'), '.zzz が未定義')

# 2-6 HTML構造
mutation('2-6 閉じられていないdiv',
         doc(full_course()).replace('</div></body>', '</body>', 1), '閉じられていないタグ')
mutation('2-6 余分な終了タグ',
         doc(full_course()).replace('<h2>第2回', '</div><h2>第2回', 1),
         '対応する開始タグのない')

# 2-7 数式エンジン
for pat, label in [('$E=mc^2$', 'インライン $...$'),
                   ('$$E=mc^2$$', 'ブロック $$...$$'),
                   (r'\(E=mc^2\)', r'\(...\)'),
                   (r'\[E=mc^2\]', r'\[...\]')]:
    mutation('2-7 数式エンジン未読込: %s' % label,
             doc(full_course() + '<p>%s</p>' % pat), '数式エンジン未読込')
baseline('2-7 KaTeXをscriptで読込なら通す',
         doc(full_course() + '<p>$E=mc^2$</p>',
             head_extra='<script src="https://cdn/katex.min.js"></script>'))
baseline('2-7 MathJaxをインライン設定なら通す',
         doc(full_course() + '<p>$E=mc^2$</p>',
             head_extra='<script>window.MathJax={tex:{}};</script>'))
mutation('2-7 本文に単語katexがあるだけ（偽陽性）',
         doc(full_course() + '<p>katex について $E=mc^2$</p>'), '数式エンジン未読込')

# --- 2026/8/23 第2次指摘への対応検体 ---
mutation('4-1 CSSコメント内の定義を誤認',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60),
             style_extra='/* .zzz{color:red} */'), '.zzz が未定義')
baseline('4-2 2つ目のstyleに定義があれば通す',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60),
             head_extra='<style>.zzz{color:red}</style>'))
# 旧版はここに doc(full_course()) を基線として置いていたが、宣言ブロック内に
# `.class` 文字列も対応する class 属性も無く、当該性質を検証していなかった
# (2026/8/23 指摘)。実際の再現条件へ置換し、変異試験として数える。
mutation('4-1 宣言ブロック内の.文字列を定義と誤認',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60),
             style_extra='.x{content:".zzz"}'), '.zzz が未定義')

# --- 2026/8/23 第3次指摘への対応検体 ---
mutation('4-2b inline scriptの文字列だけでエンジンと誤認',
         doc(full_course() + '<p>$E=mc^2$</p>',
             head_extra='<script>const label="katex";</script>'), '数式エンジン未読込')
baseline('4-1b CSS内の数式風文字列を本文数式と誤検出しない',
         doc(full_course(), head_extra='<style>.unused{content:"$E=mc^2$"}</style>'))
baseline('4-1c script内の数式風文字列を本文数式と誤検出しない',
         doc(full_course(), head_extra='<script>var s="$E=mc^2$";</script>'))

# 密度
mutation('密度: 項目数不足',
         doc(full_course().replace(ITEM * 8, ITEM * 3, 1)), '項目数'),
mutation('密度: 短すぎる項目',
         doc(full_course().replace(ITEM, '<div class="pt">短い</div>', 1)), '短すぎる項目')

# --- 2026/8/23 第4次指摘への対応検体 ---
mutation('4-1c katex風の任意script名をエンジンと誤認',
         doc(full_course() + '<p>$E=mc^2$</p>',
             head_extra='<script src="/assets/katex-notes.js"></script>'), '数式エンジン未読込')
baseline('4-1d 実運用のMathJax読込は通す',
         doc(full_course() + '<p>$E=mc^2$</p>',
             head_extra='<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>'))
mutation('4-2c 否定セレクタを定義と誤認',
         doc(full_course() + '<div class="zzz">%s</div>' % ('い' * 60),
             style_extra=':not(.zzz){color:red}'), '.zzz が未定義')
baseline('4-2d :not([属性])を含むCSSは通す',
         doc(full_course(), style_extra=':root:not([data-theme="light"]){color:red}'))
mutation('4-3 回次が漢数字',
         doc(full_course().replace('<h2>第15回 — X</h2>', '<h2>第十五回 — X</h2>', 1)),
         '漢数字')

# --- 無番号節の対応表(covered_by)がHTML側で検証されるか ---
# 台帳が「第N回は無番号節が相当する」と主張するとき、その見出しが実在するかを
# 検査する。主張を書くだけで検査しなければ根拠のない除外を素通りさせる。
_CMP = os.path.join(_SRC_BASE, C.TEST_COVERED_NOTE)
_H = '<h2 id="%s">%s</h2>' % C.TEST_COVERED_HEADING   # 台帳が相当節とする無番号見出し
with open(_CMP, encoding='utf-8') as _f:
    _cmp = _f.read()
baseline('covered_by 相当節が揃っていれば通す', _cmp, course=C.TEST_COVERED_COURSE)
mutation('covered_by 相当節の見出しが無いとFAIL',
         _cmp.replace(_H, _H.replace(C.TEST_COVERED_HEADING[1], '別の見出し'), 1),
         '台帳が第1回の相当節とする無番号見出し', course=C.TEST_COVERED_COURSE)
# 3-2 部分一致だと「<見出し>ではない」が相当節として通ってしまう
mutation('covered_by は完全一致（語を含むだけでは通さない）',
         _cmp.replace(_H, _H.replace(C.TEST_COVERED_HEADING[1], C.TEST_COVERED_HEADING[1] + 'ではない'), 1),
         '台帳が第1回の相当節とする無番号見出し', course=C.TEST_COVERED_COURSE)
# 3-3 無番号節の代役に番号付き見出しを使えてはならない
mutation('covered_by は無番号見出しに限る',
         _cmp.replace(_H, _H.replace(C.TEST_COVERED_HEADING[1], '第2回 ' + C.TEST_COVERED_HEADING[1]), 1),
         '台帳が第1回の相当節とする無番号見出し', course=C.TEST_COVERED_COURSE)

print('\n== 例外台帳のスキーマ検証 ==')
OKROW = {"reason": "r", "source": "機械確認", "date": "2026-08-23",
         "disposition": "source_missing"}


TOP_KEYS = ("exempt_courses", "dynamic_apps", "expected_last_round", "missing_rounds")


def whole(ex):
    """トップレベル4キーを補って完全な台帳にする。
    個別の検証項目を試すのに、毎回4キーを書くのは検体の意図をぼかすため。
    トップレベルの欠落そのものを試す検体では、この関数を通さない。"""
    return {k: ex.get(k, {}) for k in TOP_KEYS}


def ledger(label, ex, expect):
    errs = cn.validate_exceptions(ex)
    hit = [e for e in errs if expect in e]
    results['mutation'].append(bool(hit))
    print('  %s %-36s %s' % ('OK ' if hit else 'NG!', label,
                             (hit[0][:50] if hit else '検出できず')))


def ledger_ok(label, ex):
    errs = cn.validate_exceptions(ex)
    results['baseline'].append(not errs)
    print('  %s %-36s %s' % ('OK ' if not errs else 'NG!', label, errs[:1] or 'エラー 0'))


base_ex = {"expected_last_round": {"A": dict(OKROW, value=15)},
           "missing_rounds": {"A": [dict(OKROW, round=3)]}}
ledger_ok('台帳: 正常な検体', whole(base_ex))
ledger('4-3 missing_rounds に対応する期待最終回が無い',
       whole({"missing_rounds": {"B": [dict(OKROW, round=3)]}}),
       'expected_last_round に登録が無い')
ledger('4-4 value に真偽値 True',
       whole({"expected_last_round": {"A": dict(OKROW, value=True)}, "missing_rounds": {}}), 'value が正の整数でない')
ledger('4-4 round に真偽値 True',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=True)]}}), 'round が正の整数でない')
ledger('4-5 存在しない日付 2026-99-99',
       whole({"expected_last_round": {"A": dict(OKROW, value=15, date="2026-99-99")},
        "missing_rounds": {}}), '実在する日付でない')
ledger('source が許容値外',
       whole({"expected_last_round": {"A": dict(OKROW, value=15, source="なんとなく")},
        "missing_rounds": {}}), '許容値外')
ledger('round の重複',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3), dict(OKROW, round=3)]}}), '重複して登録')
ledger('round が想定最終回を超える',
       whole({"expected_last_round": {"A": dict(OKROW, value=5)},
        "missing_rounds": {"A": [dict(OKROW, round=9)]}}), '超えている')
ledger('必須キーの欠落',
       whole({"expected_last_round": {"A": {"value": 15, "source": "機械確認",
                                            "date": "2026-08-23"}}}),
       "'reason' が空または欠落")
# --- 第4次指摘: 構造破損と日付書式 ---
ledger('4-4 トップレベルのキーが欠落',
       {"expected_last_round": {}}, "キー 'missing_rounds' が無い")
ledger('4-4 エントリが辞書でない（配列）',
       whole({"exempt_courses": {"A": []}, "dynamic_apps": {},
        "expected_last_round": {}, "missing_rounds": {}}), "エントリが辞書でない")
ledger('4-4 missing_rounds の値が配列でない',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": "3"}}), "値が配列でない")
_norow = {k: v for k, v in OKROW.items() if k != "disposition"}
ledger('disposition が未指定',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(_norow, round=3)]}}),
       'disposition が未指定または不正')
ledger('disposition が未知の値',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3, disposition="なんとなく")]}}),
       'disposition が未指定または不正')
# 3-1 これが本命。covered_by を消すだけで検査を回避できてはならない
ledger('covered_by_unnumbered なのに covered_by が無い',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3,
                                      disposition="covered_by_unnumbered")]}}),
       'covered_by が必須')
ledger('source_missing なのに covered_by がある',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3, disposition="source_missing",
                                      covered_by=["見出し"])]}}),
       'covered_by を持てない')
ledger('covered_by が配列でない',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3, covered_by="見出し")]}}),
       'covered_by は非空の配列')
ledger('covered_by の要素が空文字',
       whole({"expected_last_round": {"A": dict(OKROW, value=15)},
        "missing_rounds": {"A": [dict(OKROW, round=3, covered_by=["  "])]}}),
       'covered_by の要素は非空の文字列')
ledger('4-5 日付が YYYY-MM-DD 形式でない（20260823）',
       whole({"expected_last_round": {"A": dict(OKROW, value=15, date="20260823")},
        "missing_rounds": {}}), "YYYY-MM-DD 形式でない")

print('\n== 学期進行中（held_through。2026/9/27追加）==')
ledger_ok('台帳: held_through=5 / value=15',
          whole({"expected_last_round": {"A": dict(OKROW, value=15, held_through=5)}}))
ledger('held_through が value を超える',
       whole({"expected_last_round": {"A": dict(OKROW, value=15, held_through=16)}}),
       'held_through は 1〜value')
ledger('held_through が 0',
       whole({"expected_last_round": {"A": dict(OKROW, value=15, held_through=0)}}),
       'held_through は 1〜value')
_saved = dict(cn.HELD_THROUGH)
cn.HELD_THROUGH[SYNTH_COURSE] = 5
try:
    baseline('合成・第1〜5回（5回まで実施済み）', doc(full_course(last=5)))
    # 実施済み範囲内の欠番は従来どおり検出しなければならない
    mutation('実施済み範囲内の欠番', doc(full_course(last=5, skip=(3,))), '欠番')
    # held_through の更新忘れ(実施済みより先の回が書かれている)を放置しない
    mutation('held_through より後の回次', doc(full_course(last=6)), 'held_through')
finally:
    cn.HELD_THROUGH.clear()
    cn.HELD_THROUGH.update(_saved)

b, m = results['baseline'], results['mutation']
print('\n基線 %d/%d 合格 / 欠陥検出 %d/%d 合格' % (sum(b), len(b), sum(m), len(m)))
sys.exit(0 if all(b) and all(m) else 1)
