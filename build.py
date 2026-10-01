# -*- coding: utf-8 -*-
"""
study-hub ビルドスクリプト

大学の学習ツール(単一HTML)を public/ へ集約し、ハブページを生成する。
デプロイ対象は public/ のみ。原本は各科目フォルダに残す(単一の情報源)。

使い方:
    python build.py                # 通常ビルド
    python build.py --placeholder  # 認証設定前の仮ページのみ生成
"""
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atomicio
import json
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
# 出力先は環境変数で差し替えられる。決定性試験が実運用の public を
# 直接再生成すると、監査のために配信物を壊しうる(2026/8/24 指摘)。
PUBLIC = os.environ.get("STUDY_HUB_PUBLIC") or os.path.join(ROOT, "public")
# 講義資料の場所・掲載する科目の一覧は、授業を特定しうる個人データなので site_config.py（非公開）に置く。
# 公開リポジトリでは site_config_example.py（架空の科目）が代わりに読まれる（siteconf.py）。
from siteconf import C  # noqa: E402
SRC_BASE = C.SRC_BASE
JST = timezone(timedelta(hours=9))

MANIFEST = [dict(item) for item in C.MANIFEST]  # 下の変換で書き換えるため複製する

# Mac/Linux では MANIFEST の Windows 表記(区切り `\`・C:\ の絶対パス)を現機の表記へ直す(2026/9/24)。
# 表記は Windows 版と共通に保ち、読み込み時にだけ変換する。変換しないと os.path.join が
# `学期\科目\講義まとめ.html` を一つのファイル名として扱い、全件「原本なし」になる。
if os.name != "nt":
    from pathlib import PureWindowsPath
    _WIN_WORKSPACE = PureWindowsPath(C.WIN_WORKSPACE)
    for _item in MANIFEST:
        for _k in ("src", "dir"):
            if _k not in _item:
                continue
            _p = PureWindowsPath(_item[_k])
            if _p.anchor:  # 作業場の絶対パス → ~/Claude 配下(外れていれば relative_to が例外で止める)
                _item[_k] = os.path.join(os.path.expanduser("~/Claude"), *_p.relative_to(_WIN_WORKSPACE).parts)
            else:
                _item[_k] = os.path.join(*_p.parts)

# 面の意匠（CSS・JS・頭・頁の印）は hub_style.py にまとめてある（2026/9/27 ObservatoryLauncher の意匠へ改修）。
from hub_style import CSS, JS, esc, sect_head, page as _face_page  # noqa: E402,F401
from dashboard import dashboard_section  # noqa: E402


def human(n):
    return "%.0f KB" % (n / 1024.0) if n < 1024 * 1024 else "%.1f MB" % (n / 1048576.0)


def page(body, spec, n_tool=0, n_course=0, nav_links="", face="hub"):
    """旧版の呼び出し形（n_tool・n_course・nav_links）を受け付けたまま、新しい面を組む。
    nav_links は頁の印（HUB / FIELDS / TIER）に置き換えたため使わない。"""
    return _face_page(body, spec, face)


def build_placeholder():
    os.makedirs(PUBLIC, exist_ok=True)
    body = ("<section class=\"sect\"><div class=\"body\"><div class=\"grid\"><div class=\"card\">"
            "<span class=\"bl\"></span><span class=\"br\"></span>"
            "<div class=\"k\">STATUS</div><div class=\"crs\">認証設定中</div>"
            "<div class=\"dsc\">Cloudflare Access の設定が完了するまで、"
            "学習ツールは配置されない。</div></div></div></div></section>")
    spec = "<b>PLACEHOLDER</b>"
    atomicio.write_text(os.path.join(PUBLIC, "index.html"), page(body, spec))
    print("placeholder written -> public/index.html")


# 学期フォルダ名 → (欧文の札, 和文の名)。大学の学期は「YYYY_春/秋」から機械的に作る。
# 大学以外の節の名は個人の事情を表しうるため site_config.py（非公開）に置く。外部リンクの節だけはコードが使う。
SPECIAL_SECTIONS = dict(getattr(C, "SPECIAL_SECTIONS", {}))
SPECIAL_SECTIONS.setdefault("_ext", ("LINKS", "外部リンク"))
SPECIAL_ORDER = [k for k in SPECIAL_SECTIONS if k != "_ext"] + ["_ext"]
SEM_RE = re.compile(r"^(\d{4})_(春|秋)$")


def semester_label(k):
    m = SEM_RE.match(k)
    if m:
        return ("%s %s" % (m.group(1), "SPRING" if m.group(2) == "春" else "FALL"),
                "%s年度 %s学期" % (m.group(1), m.group(2)))
    return SPECIAL_SECTIONS.get(k, (k.upper(), k))


# 互換: 旧版の SEMESTER_LABEL を参照する外部スクリプトのため
SEMESTER_LABEL = {k: v[1] for k, v in SPECIAL_SECTIONS.items()}


def semester_key(item):
    if item.get("url"):
        return "_ext"
    # 大学の科目以外(資格対策など)は src が学期フォルダ配下にないため、
    # sem キーで所属セクションを明示する。src に絶対パスも書ける。
    if item.get("sem"):
        return item["sem"]
    # Mac では読み込み時に区切りを `/` へ直しているため、両方の区切りで切る。
    # `\` だけで切っていたため、Mac 移行後は科目ごとに別の学期として並んでいた(2026/9/27 本人指摘)。
    return re.split(r"[\\/]", item["src"], maxsplit=1)[0]


def load_progress():
    """例外台帳の expected_last_round から、科目ごとの (まとめた回, 全回) を返す。
    held_through が無い科目は学期を終えたものとして全回とみなす。台帳が無ければ空。"""
    path = os.path.join(ROOT, "exceptions.json")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        ex = json.load(f)
    out = {}
    for k, v in ex.get("expected_last_round", {}).items():
        if k.startswith("_") or not isinstance(v, dict) or not isinstance(v.get("value"), int):
            continue
        out[k] = (v.get("held_through", v["value"]), v["value"])
    return out


def nice_step(top):
    """目盛りの刻み: 1・2・2.5・5・10 の倍数のうち、五〜七本に収まるもの。"""
    for s in (1, 2, 5, 10, 20, 50):
        if top / s <= 7:
            return s
    return 100


def progress_figure(items, progress):
    """今学期の進み: 科目ごとに何回分まとめたか。L 字の軸、細い罫の棒、今の一点だけ燠火。"""
    rows = []
    for item, size, _m in items:
        if item.get("url") or item.get("offline") or size is None or item["course"] not in progress:
            continue
        done, total = progress[item["course"]]
        rows.append((item["course"], done, total))
    if not rows:
        return ""
    top = max(t for _, _, t in rows)
    step = nice_step(top)
    top = -(-top // step) * step  # 最上段は最大値以上の刻みに揃える
    ticks = "".join("<span style=\"left:%.4f%%\">%d</span>" % (100.0 * v / top, v)
                    for v in range(0, top + 1, step))
    grid = "calc(100%%/%d)" % (top // step)
    body = []
    for name, done, total in sorted(rows, key=lambda r: (-r[1], r[0])):
        bar = "<div class=\"bar\" style=\"width:%.4f%%\"></div>" % (100.0 * done / top)
        body.append(
            "<div class=\"fr\"><div class=\"fn\">" + esc(name) + "</div>"
            "<div class=\"track\" style=\"background-size:" + grid + " 100%\">" + bar + "</div>"
            + "<div class=\"fv\">%d / %d</div></div>" % (done, total))
    total_done = sum(d for _, d, _ in rows)
    latest = max(d for _, d, _ in rows)
    concl = "%d科目で計%d回分をまとめた ∧ 最も進んだ科目は第%d回まで" % (len(rows), total_done, latest)
    return ("<figure class=\"fig\"><div class=\"fh\"><span class=\"lbl\">PROGRESS</span>"
            "<span class=\"nm\" style=\"font-size:14px;color:var(--muted)\">講義まとめの進み</span>"
            "<span class=\"rule\"></span><span class=\"mt\">回 ∧ %d刻み</span></div>" % step
            + "".join(body)
            + "<div class=\"axis\"><div></div><div class=\"ticks\">" + ticks + "</div>"
            "<div class=\"unit\">回</div></div><p class=\"concl\">" + concl + "</p></figure>")


def card(item, size, mtime):
    code = "<div class=\"k\">" + esc(item["code"]) + "<span class=\"new\">NEW</span></div>"
    head = ("<span class=\"bl\"></span><span class=\"br\"></span>" + code
            + "<div class=\"crs\">" + esc(item["course"]) + "</div>"
            "<div class=\"ttl\">" + esc(item["title"]) + "</div>")
    if size == "offline":
        # 非掲載の科目（教員の指示などで中身をネットに置かない）。存在だけを示し、リンクも中身も持たない
        return ("<div class=\"card offline rise\">" + head + "<div class=\"dsc\">" + esc(item["desc"]) + "</div>"
                "<div class=\"meta\">NOT ONLINE</div></div>")
    if size == "url":
        return ("<a class=\"card rise\" href=\"" + esc(item["url"]) + "\" target=\"_blank\" "
                "rel=\"noopener noreferrer\">" + head + "<div class=\"dsc\">" + esc(item["desc"]) + "</div>"
                "<div class=\"meta\">EXTERNAL ↗</div></a>")
    if size is None:
        return ("<div class=\"card miss rise\">" + head + "<div class=\"dsc\">原本が見つからない。</div>"
                "<div class=\"meta\">MISSING</div></div>")
    href = esc(item["dest"].replace("/index.html", "/"))
    return ("<a class=\"card rise\" href=\"" + href + "\" data-mtime=\"%d\">" % int(mtime.timestamp())
            + head + "<div class=\"dsc\">" + esc(item["desc"]) + "</div>"
            "<div class=\"meta\">更新 " + mtime.strftime("%Y-%m-%d") + "</div></a>")


def build():
    # フォルダごと削除してから作り直すと、Windowsのウイルス対策ソフトが
    # 直前に書き込んだファイルを一瞬ロックし、rmtreeがPermissionErrorで
    # 失敗することがある。上書きコピーで十分なため、丸ごと削除はしない。
    # MANIFESTから外れた古い出力が残る点だけ運用上の注意点。
    os.makedirs(PUBLIC, exist_ok=True)

    groups, courses, found, missing = {}, set(), [], []
    for item in MANIFEST:
        sk = semester_key(item)
        courses.add(item["course"])
        # 非掲載項目: 科目の存在だけを札で示す。原本を持たず、何も複製しない。
        if item.get("offline"):
            groups.setdefault(sk, []).append((item, "offline", None))
            continue
        # 外部リンク項目: ファイル複製をせず、URLカードとして扱う。
        if item.get("url"):
            groups.setdefault(sk, []).append((item, "url", None))
            found.append(item)
            continue
        # ディレクトリ項目: PWA(Service Worker と manifest)は実体ファイルを要するため、
        # 単一HTMLの複製では足りない。dir を持つ項目はフォルダごと複製する。
        if item.get("dir"):
            srcdir = item["dir"] if os.path.isabs(item["dir"]) else os.path.join(SRC_BASE, item["dir"])
            index = os.path.join(srcdir, "index.html")
            if not os.path.isdir(srcdir) or not os.path.isfile(index):
                missing.append(item)
                groups.setdefault(sk, []).append((item, None, None))
                continue
            dstdir = os.path.join(PUBLIC, item["dest"].rstrip("/").replace("/", os.sep))
            os.makedirs(dstdir, exist_ok=True)
            for name in sorted(os.listdir(srcdir)):
                sp = os.path.join(srcdir, name)
                if os.path.isfile(sp):
                    shutil.copy2(sp, os.path.join(dstdir, name))
            st = os.stat(index)
            groups.setdefault(sk, []).append(
                (item, st.st_size, datetime.fromtimestamp(st.st_mtime, JST)))
            found.append(item)
            continue
        src = os.path.join(SRC_BASE, item["src"])
        if not os.path.isfile(src):
            missing.append(item)
            groups.setdefault(sk, []).append((item, None, None))
            continue
        dst = os.path.join(PUBLIC, item["dest"].replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        st = os.stat(src)
        groups.setdefault(sk, []).append(
            (item, st.st_size, datetime.fromtimestamp(st.st_mtime, JST)))
        found.append(item)

    # 並び: 今学期（最も新しい大学の学期）を先頭に開いて置き、過去の学期は新しい順に畳む。
    # 大学以外の節（site_config の SPECIAL_SECTIONS・外部リンク）はその後に畳んで置く。
    sems = sorted((k for k in groups if SEM_RE.match(k)),
                  key=lambda k: (int(k[:4]), 0 if k.endswith("春") else 1), reverse=True)
    current = sems[0] if sems else None
    ordered = sems + [k for k in SPECIAL_ORDER if k in groups]
    ordered += [k for k in groups if k not in ordered]
    progress = load_progress()

    parts = []
    for sk in ordered:
        items = sorted(groups[sk], key=lambda t: t[0]["course"])
        n_courses = len({t[0]["course"] for t in items})
        label, name = semester_label(sk)
        is_now = sk == current
        meta = ("%d COURSES" % n_courses) + ("" if n_courses == len(items) else " ∧ %d TOOLS" % len(items))
        parts.append("<details class=\"sect" + (" now" if is_now else "") + "\" id=\"s-" + esc(sk) + "\""
                     + (" open" if is_now else "") + "><summary>"
                     + sect_head(label + (" ∧ NOW" if is_now else ""), name, meta, chevron=True)
                     + "</summary><div class=\"body\">")
        if is_now:
            parts.append(progress_figure(items, progress))
        parts.append("<div class=\"grid\">" + "".join(card(*t) for t in items) + "</div></div></details>")

    # 生成時刻は成果物へ埋め込まれるため、そのままでは同じ入力でも分をまたぐと
    # ハッシュが変わる。決定性の検査ができないので、環境変数で固定できるようにする
    # (2026/8/24 指摘。「2回連続で一致した」は同一分内だっただけであった)。
    now = os.environ.get("STUDY_HUB_BUILD_TIME") or datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    spec = ("<span class=\"sp\"><b data-count=\"tools\">" + str(len(found)) + "</b> TOOLS</span>"
            "<span class=\"sp\"><b data-count=\"courses\">" + str(len(courses)) + "</b> COURSES</span>"
            "<span class=\"sp\">BUILT <b>" + now + "</b> JST</span>")

    # 先頭のダッシュボード（今日の授業・締切・復習・検索）。見出しの索引（extract_index.py の出力）で回へ飛ばす
    hp = os.path.join(ROOT, "headings.json")
    headings = json.load(open(hp, encoding="utf-8")) if os.path.isfile(hp) else []
    dash = dashboard_section(C, headings, MANIFEST)

    atomicio.write_text(os.path.join(PUBLIC, "index.html"), page(dash + "".join(parts), spec, face="hub"))

    total = sum(os.path.getsize(os.path.join(r, x))
                for r, _, fs in os.walk(PUBLIC) for x in fs)
    print("built: %d tools / %d courses / %s" % (len(found), len(courses), human(total)))
    for m in missing:
        print("  MISSING: " + (m.get("src") or m.get("dir")))  # dir 項目は src を持たない
    print("output -> " + PUBLIC)


if __name__ == "__main__":
    if "--placeholder" in sys.argv:
        build_placeholder()
    else:
        build()
