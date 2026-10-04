# -*- coding: utf-8 -*-
"""site_config.py の見本（公開用・架空の科目）。

実際の運用では、同じ形の site_config.py を作ってこのフォルダに置く（.gitignore 済みで公開されない）。
科目名・資料の置き場所・説明文・評価文など、授業や所属を特定しうる情報はすべてそちらに書く。
"""
import os

# 講義資料（講義まとめの原本 HTML と PDF）の置き場所。学期フォルダ\科目フォルダ\ファイル の構成
SRC_BASE = os.environ.get("STUDY_HUB_SRC_BASE") or os.path.expanduser("~/lecture-notes")
# Windows 機での作業場（MANIFEST に絶対パスを書いた項目を、Mac の ~/Claude へ読み替える基準）
WIN_WORKSPACE = r"C:\Users\me\Desktop\Claude"

# ハブに並べる項目。src は SRC_BASE からの相対パス（区切りは \ でも / でもよい）
MANIFEST = [
    {
        "course": "科目A", "code": "AAA",
        "title": "講義まとめ", "desc": "第1〜14回の要点。",
        "src": r"2026_春\科目A\講義まとめ.html", "dest": "aaa-notes/index.html",
    },
    {
        "course": "科目B", "code": "BBB",
        "title": "講義まとめ", "desc": "第1回の要点。",
        "src": r"2026_秋\科目B\講義まとめ.html", "dest": "bbb-notes/index.html",
    },
    {
        "course": "問題集", "code": "QZ",
        "title": "期末対策", "desc": "自己採点式の問題集（JS で問題を生成するアプリ）。",
        "src": r"2026_春\科目C\期末対策.html", "dest": "quiz/index.html",
    },
    # 非掲載の科目: 中身を載せず、科目があることだけを札で示す（offline。sem で節を指定）
    {
        "course": "科目D", "code": "DDD", "sem": "2026_秋", "offline": True,
        "title": "非掲載", "desc": "中身をネットに載せない科目の例。",
    },
    # フォルダごと複製するアプリ（PWA など）。sem で所属する節を明示する
    {
        "course": "道具", "code": "TL", "sem": "_juku",
        "title": "指導台帳", "desc": "フォルダごと配信するアプリの例。",
        "dir": r"tools\app\public", "dest": "tool/",
    },
    # 外部リンク: url を持つ項目は複製せず外部カードとして描画する
    {
        "course": "外部", "code": "EXT",
        "title": "外部ツール", "desc": "別ホストで公開しているツールの例。",
        "url": "https://example.com/",
    },
]

# 分野別インデックス: 科目名 -> 分野（複数可）と、分野の並び
COURSE_TAGS = {
    "科目A": ["分野1"],
    "科目B": ["分野1", "分野2"],
}
FIELD_ORDER = ["分野1", "分野2"]

# ティア表の冒頭の説明（HTML）と、(段, 段の説明, [(科目, 評価文), ...]) の並び
TIER_INTRO = [
    "一次資料に基づく暫定評価。個人の学習優先度の目安である。",
]
TIER_DATA = [
    ("S", "体系性・厳密性・教育設計のいずれも高水準", [
        ("科目A", "評価文。"),
    ]),
    ("要確認", "資料内の主張について、通説・根拠・注記の確認が必要", [
        ("科目B", "評価文。"),
    ]),
]

# 網羅性表（gen_coverage_manifest.py）の科目別の例外
COVERAGE_OFFSET = {"科目A": 1}        # 回次 = ファイル番号 + offset となる科目
COVERAGE_MANUAL = {"科目B"}           # 機械では回次を決められない科目（人手で確定する）

# 検査器の試験（test_check_notes.py）が使う実データ。実在する講義まとめを指す
TEST_SYNTH_COURSE = "科目A"           # 想定最終回15・無番号節の対応表を持たない科目
TEST_REAL_NOTE = os.path.join("2026_春", "科目A", "講義まとめ.html")
TEST_REAL_COURSE = "科目A"
TEST_COVERED_COURSE = "科目B"         # 無番号節の対応表（covered_by）を持つ科目
TEST_COVERED_NOTE = os.path.join("2026_秋", "科目B", "講義まとめ.html")
TEST_COVERED_HEADING = ("s2", "導入")  # 台帳が第1回の相当節とする無番号見出し (id, 見出し)

# ハブの節のうち大学の学期以外のもの（MANIFEST の sem で指定）。キー → (欧文の札, 和文の名)
SPECIAL_SECTIONS = {
    "_juku": ("TOOLS", "道具"),
    "_ext": ("LINKS", "外部リンク"),
}

# 索引を作らない JS 動的生成の頁（extract_index.py）
DYNAMIC_APPS = ["quiz/index.html"]

# 独自設計のアプリ頁（notes_skin.py）: 配信先の先頭 → 意匠の種類（quiz / workbook / sheet）、
# アプリが自前で明暗を覚える localStorage のキー
APP_KINDS = {"quiz": "quiz"}
APP_THEME_KEYS = []

# ---- ダッシュボード（dashboard.py）。実際の時間割・締切は site_config.py（非公開）に書く。以下は架空の例 ----
TERM = {"name": "2026年度 秋学期", "start": "2026-09-24", "end": "2027-01-31"}
PERIODS = {1: "09:00", 2: "10:40", 3: "13:00", 4: "14:40", 5: "16:20"}
TIMETABLE = [{"day": 0, "period": 2, "course": "科目A"}, {"day": 2, "period": 3, "course": "科目B"}]
ON_DEMAND = [{"day": 0, "time": "15:00", "course": "科目C"}]
CANCELLED = [("科目B", "2026-11-18")]
DEADLINES = [{"at": "2026-10-08T23:59", "course": "科目A", "label": "第2回 課題"}]
LECTURES = [("科目A", 1, "2026-09-28"), ("科目B", 1, "2026-09-30")]
REVIEW_INTERVALS = [1, 3, 7, 14, 30]

# ---- 分野の重なり（euler.py）。例：科目Cは「分野1」と「分野2」の両方にまたがる ----
SCOPE_TAGS = {"科目C": ["分野1", "分野2"]}
