# -*- coding: utf-8 -*-
"""原子的なファイル書き出し。

途中で異常終了した場合、従来の `open(path,'w')` は**内容が欠けたファイルを
正しい成果物として残す**。証跡・索引・原本HTMLのいずれもこの状態を機械検査で
見分けられないため、書き出しは一時ファイル経由で行い、完了時に置換する。

`extract_index.py` は講義まとめの原本HTMLを直接上書きするため、
ここが最も損害の大きい経路である(2026/8/23 Codex計画 §7)。
"""
import json
import os
import tempfile


def write_text(path, text, encoding='utf-8'):
    """path へ text を原子的に書き出す。成功時のみ既存ファイルを置換する。"""
    d = os.path.dirname(os.path.abspath(path)) or '.'
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tmp-', suffix='.part')
    try:
        # newline は既定(変換あり)。newline='' にすると既存ファイルが一斉に
        # LF へ書き換わり、無関係な差分を生む。
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        # Windows の os.replace は同一ボリューム上で原子的に置換する
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_json(path, obj, **kw):
    kw.setdefault('ensure_ascii', False)
    kw.setdefault('indent', 2)
    write_text(path, json.dumps(obj, **kw))
