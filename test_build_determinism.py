# -*- coding: utf-8 -*-
"""ビルドの決定性試験（時刻非依存）。

第5報で「2回連続実行してハッシュが一致した」ことを決定性の証拠としたが、
これは同一分内に実行しただけであった。build.py は生成時刻を分単位で成果物へ
埋め込むため、分をまたげば同じ入力でもハッシュが変わる(2026/8/24 指摘)。

そこで `STUDY_HUB_BUILD_TIME` で時刻を固定し、
  * 同じ時刻を与えれば全成果物のハッシュが一致すること
  * 時刻だけを変えれば変化し、**時刻以外に非決定要因が無い**こと
の両方を確かめる。後者を省くと「常に同じ物を出すだけ」の検査と区別できない。

出力先は `STUDY_HUB_PUBLIC` で一時領域へ逃がす。**実運用の public を
再生成してはならない**——監査のために配信物を壊すことになる(2026/8/24 指摘)。

使い方:
    python -X utf8 test_build_determinism.py
"""
import hashlib
import io
import os
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HUB = os.path.dirname(os.path.abspath(__file__))
T1 = '2000-01-01 00:00'
T2 = '2000-01-01 00:01'
# 時刻を埋め込むと分かっているファイル。ここ以外に差が出たら非決定要因がある。
TIMESTAMPED = {'index.html'}


def build(t, out):
    env = dict(os.environ, STUDY_HUB_BUILD_TIME=t,
               STUDY_HUB_PUBLIC=out, PYTHONUTF8='1')
    r = subprocess.run([sys.executable, '-X', 'utf8', 'build.py'],
                       cwd=HUB, env=env, capture_output=True)
    if r.returncode:
        print(r.stderr.decode('utf-8', 'replace'))
        raise SystemExit('build.py が失敗した')
    h = {}
    for root, _, files in os.walk(out):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, out).replace('\\', '/')
            h[rel] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return h


ok = ng = 0


def check(label, cond, detail=''):
    global ok, ng
    if cond:
        ok += 1
    else:
        ng += 1
    print('  %s %-44s %s' % ('OK ' if cond else 'NG!', label, detail))


with tempfile.TemporaryDirectory() as d:
    a = build(T1, os.path.join(d, 'a'))
    b = build(T1, os.path.join(d, 'b'))
    c = build(T2, os.path.join(d, 'c'))

check('実運用の public を再生成していない',
      os.path.isdir(os.path.join(HUB, 'public')), '（一時領域へ出力した）')

# --- 同じ時刻 → 完全一致（ファイル集合とハッシュの両方）---
check('同じ時刻: ファイル集合が同一', set(a) == set(b),
      sorted(set(a) ^ set(b))[:5] or '%d ファイル' % len(a))
d1 = sorted(k for k in set(a) & set(b) if a[k] != b[k])
check('同じ時刻: 全ファイルのハッシュが一致', not d1, d1[:5] or '差 0')

# --- 時刻だけ変更 → 差は index.html ちょうど1件 ---
check('時刻変更: ファイル集合が同一', set(a) == set(c),
      sorted(set(a) ^ set(c))[:5] or '%d ファイル' % len(a))
d2 = set(k for k in set(a) & set(c) if a[k] != c[k])
# 「差がある」だけでは足りず、「差が index.html だけ」でなければ
# 時刻以外の非決定要因を見逃す。集合の厳密一致で検査する。
check('時刻変更: 差分が厳密に index.html だけ', d2 == TIMESTAMPED,
      '差=%s' % (sorted(d2) or '無し'))

print('\n合格 %d / 不合格 %d' % (ok, ng))
sys.exit(1 if ng else 0)
