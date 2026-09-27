# -*- coding: utf-8 -*-
"""atomicio.py の障害試験。

原子書込みは「壊れた成果物を残さない」ことが目的であり、正常系だけを見ても
その目的を検証したことにならない。**書込みの各段階を強制的に失敗させ、
旧内容が残り一時ファイルが消えること**を確かめる(2026/8/24 Codex指摘)。

使い方:
    python -X utf8 test_atomicio.py
"""
import glob
import importlib.util
import io
import os
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HUB = os.path.dirname(os.path.abspath(__file__))
_s = importlib.util.spec_from_file_location('atomicio', os.path.join(HUB, 'atomicio.py'))
atomicio = importlib.util.module_from_spec(_s)
_s.loader.exec_module(atomicio)

ok = 0
ng = 0


def check(label, cond, detail=''):
    global ok, ng
    if cond:
        ok += 1
        print('  OK  %-44s %s' % (label, detail))
    else:
        ng += 1
        print('  NG! %-44s %s' % (label, detail))


def parts(d):
    return glob.glob(os.path.join(d, '.tmp-*.part'))


class Boom(Exception):
    pass


# ---------------------------------------------------------------- 正常系
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'a.txt')
    atomicio.write_text(p, 'OLD\n')
    atomicio.write_text(p, 'NEW\n')
    check('正常系: 内容が置換される',
          open(p, encoding='utf-8').read() == 'NEW\n')
    check('正常系: 一時ファイルが残らない', not parts(d))

    # 新規作成（既存なし・中間ディレクトリも作る）
    q = os.path.join(d, 'sub', 'dir', 'b.txt')
    atomicio.write_text(q, 'X')
    check('正常系: 中間ディレクトリを作って新規作成', os.path.isfile(q))

# -------------------------------------------------- 置換段階での失敗
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'a.txt')
    atomicio.write_text(p, 'OLD\n')
    real = os.replace
    os.replace = lambda a, b: (_ for _ in ()).throw(Boom('replace failed'))
    try:
        atomicio.write_text(p, 'NEW\n')
        raised = False
    except Boom:
        raised = True
    finally:
        os.replace = real
    check('置換失敗: 例外がそのまま伝播する', raised)
    check('置換失敗: 旧内容が保たれる',
          open(p, encoding='utf-8').read() == 'OLD\n')
    check('置換失敗: 一時ファイルが残らない', not parts(d), parts(d))

# ------------------------------------------------ 書込み段階での失敗
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'a.txt')
    atomicio.write_text(p, 'OLD\n')
    # 一時ファイルへ書いた直後(fsync)で落とす。str 派生型では f.write が
    # 失敗しないため、故障注入としては成立しなかった(初版の誤り)。
    real = os.fsync
    os.fsync = lambda fd: (_ for _ in ()).throw(Boom('fsync failed'))
    try:
        atomicio.write_text(p, 'NEW\n')
        raised = False
    except Boom:
        raised = True
    finally:
        os.fsync = real
    check('書込み失敗: 例外がそのまま伝播する', raised)
    check('書込み失敗: 旧内容が保たれる',
          open(p, encoding='utf-8').read() == 'OLD\n')
    check('書込み失敗: 一時ファイルが残らない', not parts(d), parts(d))

# -------------------------------------------------------- 内容の忠実性
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'u.txt')
    # 非BMP・結合文字・全角を含む実データ相当
    src = 'あア亜𝓪é゙🄰 — 「見出し」\n2行目\n'
    atomicio.write_text(p, src)
    check('内容: Unicodeが往復して一致',
          open(p, encoding='utf-8').read() == src)

    # 改行は既定の変換に従う（newline='' にすると既存HTMLが一斉にLFへ変わる）
    b = open(p, 'rb').read()
    want_crlf = (os.linesep == '\r\n')
    check('改行: プラットフォーム既定の変換に従う',
          (b.count(b'\r\n') == 2) if want_crlf else (b.count(b'\r') == 0),
          'CRLF=%d LF=%d' % (b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))

# -------------------------------------------------------------- JSON
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'x.json')
    atomicio.write_json(p, {"日本語": [1, 2]})
    t = open(p, encoding='utf-8').read()
    check('write_json: 非ASCIIをエスケープしない', '日本語' in t)
    import json
    check('write_json: 読み戻せる', json.load(open(p, encoding='utf-8'))["日本語"] == [1, 2])

# ------------------------------------------- 一時ファイルは同一ディレクトリ
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'a.txt')
    seen = {}
    real_mkstemp = tempfile.mkstemp

    def spy(*a, **kw):
        seen['dir'] = kw.get('dir')
        return real_mkstemp(*a, **kw)

    tempfile.mkstemp = spy
    try:
        atomicio.write_text(p, 'X')
    finally:
        tempfile.mkstemp = real_mkstemp
    # 別ボリュームだと os.replace がコピー＋削除へ退化し原子性を失う
    check('一時ファイルは出力先と同一ディレクトリ',
          seen.get('dir') and os.path.samefile(seen['dir'], d), seen.get('dir'))

print('\n合格 %d / 不合格 %d' % (ok, ng))
sys.exit(1 if ng else 0)
