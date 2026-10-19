# -*- coding: utf-8 -*-
"""専門演習の個別説明会一覧表（PDF・5頁）を、担任者×日付のセル単位で zemi.json の "schedule" に取り込む。

セルの原文（raw）はそのまま残し、表示のために「開始時刻・場所」へ分解した値（slots・place）を添える。
時限は大学の標準時程で時刻に換算する（昼休みは一覧表の注記「12:20頃から開始予定」）。

    python -X utf8 zemi_sched.py <個別説明会一覧表.pdf>
"""
import json
import os
import re
import sys
import unicodedata

import fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "zemi.json")
YEAR = 2026
PERIOD = {"1": ("9:00", "10:30"), "2": ("10:40", "12:10"), "3": ("13:00", "14:30"),
          "4": ("14:40", "16:10"), "5": ("16:20", "17:50")}
LUNCH = ("12:20", "13:00")
sys.path.insert(0, ROOT)
try:
    import site_config   # 氏名の表記ゆれの対応（実名を含むので git 管理外の site_config に置く）
    ALIAS = getattr(site_config, "ZEMI_NAME_ALIAS", {})
except ImportError:
    ALIAS = {}


def key(name):
    """氏名の表記ゆれを吸収する鍵（空白・中黒・読み仮名・ミドルネームを除く）。"""
    n = unicodedata.normalize("NFKC", name)
    n = re.sub(r"[（(].*?[）)]|※", "", n)
    n = re.sub(r"[\s・]", "", n)
    for x in ALIAS.get("drop", []):
        n = n.replace(x, "")
    return ALIAS.get("map", {}).get(n, n)


def hm(s):
    s = unicodedata.normalize("NFKC", s)
    m = re.match(r"(\d{1,2}):(\d{2})", s)
    return "%d:%s" % (int(m.group(1)), m.group(2)) if m else None


def parse_cell(raw):
    """「3限、4限@A101」「12:15～13:30＠A102」「13：30、14：00、…@A103」などを (slots, place) に。"""
    s = unicodedata.normalize("NFKC", raw.replace("\n", ""))
    place = None
    if "@" in s:
        s, place = s.rsplit("@", 1)
        place = place.strip()
    slots = []
    for part in [p.strip() for p in re.split(r"[、,]", s) if p.strip()]:
        m = re.match(r"^(\d)限$", part)
        if m:
            a, b = PERIOD[m.group(1)]
            slots.append({"label": "%s限" % m.group(1), "start": a, "end": b})
            continue
        if part.startswith("昼休み"):
            slots.append({"label": "昼休み", "start": LUNCH[0], "end": LUNCH[1]})
            continue
        m = re.match(r"^(\d{1,2}:\d{2})\s*[~～\-]\s*(\d{1,2}:\d{2})$", part)
        if m:
            slots.append({"label": "", "start": hm(m.group(1)), "end": hm(m.group(2))})
            continue
        m = re.match(r"^(\d{1,2}:\d{2})$", part)
        if m:
            slots.append({"label": "", "start": hm(m.group(1)), "end": None})
            continue
        slots.append({"label": part, "start": None, "end": None})
    return slots, place


def date_of(head):
    m = re.match(r"(\d{1,2})/(\d{1,2})\((.)\)", unicodedata.normalize("NFKC", head))
    return ("%d-%02d-%02d" % (YEAR, int(m.group(1)), int(m.group(2))), m.group(3)) if m else (None, None)


def join_urls(text):
    """表の幅で折り返された URL をつなぐ（URL の行の次の、空白を含まない英数字だけの行を続きとみなす）。"""
    out = []
    for ln in text.split("\n"):
        if out and re.match(r"^https?://", out[-1].split(" ")[-1]) and re.fullmatch(r"[A-Za-z0-9?=&._/%:+-]+", ln) and not re.match(r"^\d{1,2}/\d", ln):
            out[-1] += ln
        else:
            out.append(ln)
    return "\n".join(out)


def realtime_sessions(text):
    """リアルタイム配信のセルから (日付, 開始, 終了, URL) を取り出す。日付の行の後に来る最初の URL を対応づける。"""
    out, pend = [], []
    for ln in text.split("\n"):
        n = unicodedata.normalize("NFKC", ln)
        if re.match(r"^https?://", n):
            for x in pend:
                x["url"] = n
            out += pend
            pend = []
            continue
        ds = re.findall(r"(\d{1,2})/(\d{1,2})", n)
        if ds and re.match(r"^\d{1,2}/\d", n):   # 行頭が日付の行だけ（注記の「(m/dのみA102)」などは除く）
            m = re.search(r"(\d{1,2}:\d{2})\s*[-~～]\s*(\d{1,2}:\d{2})", n)
            st, en = (hm(m.group(1)), hm(m.group(2))) if m else (None, None)
            if not m and "昼休" in n:   # 「昼休12:20～」は開始だけ（終了は書かれていない）
                m2 = re.search(r"(\d{1,2}:\d{2})", n)
                st, en = (hm(m2.group(1)) if m2 else LUNCH[0]), None
            for mo, da in ds:
                pend.append({"date": "%d-%02d-%02d" % (YEAR, int(mo), int(da)), "start": st, "end": en, "url": None})
        elif pend and not n.startswith("・") and ("昼休" in n or re.search(r"\d{1,2}:\d{2}", n)):
            m = re.search(r"(\d{1,2}:\d{2})", n)
            for x in pend:
                if not x["start"]:
                    x["start"], x["end"] = (hm(m.group(1)) if m else LUNCH[0]), None
    out += pend
    # 学内で視聴するための開放教室（「A101を開放します」「(m/dのみA102)」）
    flat = unicodedata.normalize("NFKC", text.replace("\n", ""))
    room = re.search(r"(S\d{3})を開放", flat)
    only = {"%d-%02d-%02d" % (YEAR, int(a), int(b)): r for a, b, r in re.findall(r"(\d{1,2})/(\d{1,2})のみ(S\d{3})", flat)}
    for x in out:
        x["room"] = only.get(x["date"], room.group(1) if room else None)
    return out


def main():
    pdf = sys.argv[1]
    d = fitz.open(pdf)
    sched = {"source": "個別説明会一覧表（2026年10月19日時点）", "notes": [], "inperson": [], "online": [], "other": []}
    for i, p in enumerate(d):
        t = p.find_tables().tables[0]
        blocks = [b for b in p.get_text("blocks") if b[3] <= t.bbox[1] + 2]
        notes = [b[4].strip() for b in blocks]
        if i < 3:   # 日付の列の真上に置かれた注記（例：避難訓練）は、その日付に結びつける
            cells = t.rows[0].cells
            for b in blocks:
                cx = (b[0] + b[2]) / 2
                for j, c in enumerate(cells[1:], start=1):
                    if c and c[0] <= cx <= c[2] and not b[4].lstrip().startswith(("・", "●")):
                        date, _ = date_of(t.extract()[0][j])
                        txt = re.sub(r"\s+", "", unicodedata.normalize("NFKC", b[4]))
                        sched.setdefault("daynotes", {}).setdefault(date, []).append(txt)
        sched["notes"].append({"page": i + 1, "lines": [x for n in notes for x in n.split("\n")]})
        rows = t.extract()
        head = rows[0]
        if i < 3:
            for r in rows[1:]:
                for j, cell in enumerate(r[1:], start=1):
                    if not (cell or "").strip():
                        continue
                    date, dow = date_of(head[j])
                    slots, place = parse_cell(cell)
                    sched["inperson"].append({"name": r[0], "key": key(r[0]), "date": date, "dow": dow,
                                              "raw": cell, "slots": slots, "place": place})
        elif i == 3:
            for r in rows[1:]:
                rt = join_urls(r[1] or "")
                sched["online"].append({"name": r[0], "key": key(r[0]), "realtime": rt,
                                        "sessions": realtime_sessions(rt) if rt.strip() != "なし" else [],
                                        "ondemand": (r[2] or "").strip()})
        else:
            for r in rows[1:]:
                sched["other"].append({"name": r[0], "key": key(r[0]), "text": r[1] or ""})
    data = json.load(open(DATA, encoding="utf-8"))
    keys = {key(t["name"]): t["page"] for t in data["teachers"]}
    miss = sorted({x["name"] for grp in ("inperson", "online", "other") for x in sched[grp] if x["key"] not in keys})
    for grp in ("inperson", "online", "other"):
        for x in sched[grp]:
            x["page"] = keys.get(x["key"])
    data["schedule"] = sched
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("対面 %d 件 / 配信 %d 名 / その他 %d 名 / 対応の取れない氏名: %s" % (
        len(sched["inperson"]), len(sched["online"]), len(sched["other"]), miss or "なし"))


if __name__ == "__main__":
    main()
