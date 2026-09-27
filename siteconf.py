# -*- coding: utf-8 -*-
"""個人データの読み込み口。

授業や所属を特定しうる情報（科目名・資料の場所・説明文・評価文・検査の科目別例外）は
site_config.py に置き、公開リポジトリから外している（.gitignore）。無ければ、同じ形で
架空の科目を並べた site_config_example.py を読むので、公開版だけでも一通り動く。
"""
try:
    import site_config as C  # noqa: F401
except ImportError:  # 公開リポジトリだけを取得した場合
    import site_config_example as C  # noqa: F401
