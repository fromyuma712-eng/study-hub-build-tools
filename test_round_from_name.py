# -*- coding: utf-8 -*-
"""gen_coverage_manifest.round_from_name の検体。

旧版は「ファイル名の最後の数字」を回次としており、年号・版数・ハッシュを
そのまま回次に採っていた。網羅性検査の対象表 308 行すべてがこの規則で
作られていたため、**確認する前に対象表自体を直す必要があった**(2026/8/24)。

使い方:
    python -X utf8 test_round_from_name.py
"""
import io
import os
import re
import sys
import unicodedata

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HUB = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HUB, 'gen_coverage_manifest.py'), encoding='utf-8').read()
i = src.index('def round_from_name(')
j = src.index('\ndef ', i + 10)
ns = {'re': re, 'unicodedata': unicodedata, 'os': os}
exec(src[i:j], ns)
round_from_name = ns['round_from_name']

# (ファイル名, 想定最終回, 期待する回次)
CASES = [
    # 「第N回」の明示が最優先。末尾の年号に引きずられない
    ('第10回　ユダヤ民族とアメリカ2024.pdf', 15, 10),
    ('第１５回（最後の余談）2025.pdf', 15, 15),          # 全角数字
    ('第4回レポート_Word課題2.pdf', 15, 4),              # 後続の課題番号に負けない
    ('第12回_アントレプレナーシップを知る_(授業版)_-_2025_0630.pdf', 15, 12),

    # ハッシュ名は回次を持たない。推測せず人手へ回す
    ('46bf82cda43194f718d2e8ea911855fd.pdf', 15, None),
    ('122af854e3c518f1.pdf', 15, None),
    ('d295bf04fee3590f.pdf', 15, None),

    # 「NofM」形式。曜日時限(「火5」)を回次と誤ってはならない
    ('XXXX Course Platform 5of15火.pdf', 15, 5),
    ('XXXX Course Platform火5  7of15.pdf', 15, 7),

    # 連番形式。版数(v2)を拾わない
    ('科目A-01v2.pdf', 15, 1),
    ('科目A-13.pdf', 15, 13),

    # 想定最終回を超える数しか無ければ決めない
    ('科目B25.pdf', 15, None),
    ('資料2024.pdf', 15, None),                          # 年号のみ
    ('スケジュール.pdf', 15, None),                       # 数字なし
]

ok = ng = 0
for base, last, want in CASES:
    got = round_from_name(base, last)
    if got == want:
        ok += 1
        print('  OK  %-46s -> %s' % (base[:46], got))
    else:
        ng += 1
        print('  NG! %-46s -> %s（期待 %s）' % (base[:46], got, want))

print('\n合格 %d / 不合格 %d' % (ok, ng))
sys.exit(1 if ng else 0)
