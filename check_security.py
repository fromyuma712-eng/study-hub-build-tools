# -*- coding: utf-8 -*-
"""配信物（public/）の安全検査。deploy の前に必ず通す。FAIL があれば配信しない。
  1. 保護ヘッダ（_headers）と robots.txt が security.py の出力どおりにある
  2. 頁が読み込む外部資源（script src・stylesheet・フォント・@import・url()）が、許可したホストだけ
  3. 個人情報・秘密の混入がない（メールアドレス・電話番号・学籍番号の実値・鍵やトークン・端末の絶対パス・Wi-Fi の実パスワード）
  4. 配布してはならない種類のファイルがない（.py・.env・.map・.xlsx・.pdf・.md・.docx・秘密の設定）
    python -X utf8 check_security.py
"""
import os
import re
import sys

import security

PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
ALLOWED_HOSTS = {"cdn.jsdelivr.net", "fonts.googleapis.com", "fonts.gstatic.com"}
BAD_EXT = {".py", ".pyc", ".env", ".map", ".xlsx", ".xls", ".pdf", ".md", ".docx", ".pptx", ".key", ".pem", ".sqlite", ".db", ".log"}
ALLOWED_TXT = {"robots.txt"}
SECRET = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "メールアドレス"),
    (re.compile(r"(?<![0-9])0[0-9]{1,3}-[0-9]{2,4}-[0-9]{4}(?![0-9])"), "電話番号"),
    (re.compile(r"ビ\s?[0-9]{2}-[0-9]{4}"), "学籍番号"),
    (re.compile(r"AKIA[0-9A-Z]{12,}|sk-[A-Za-z0-9]{20,}|eyJhbGci[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY"), "鍵・トークン"),
    (re.compile(r"/Users/[a-z]+/|C:\\Users\\|GoogleDrive-|CloudDocs"), "端末の絶対パス"),
    (re.compile(r"(?:Wi-?Fi|WiFi|ＷｉＦｉ|SSID)[^<。]{0,40}パスワード\s*(?:は|：|:)\s*[A-Za-z0-9!-/:-@]{6,}"), "Wi-Fi の実パスワード"),
]
EXT_URL = re.compile(r"""(?:<script[^>]+src=["']|<link[^>]+href=["']|@import\s+(?:url\()?["']?|url\(["']?)(https?:)?//([a-zA-Z0-9.-]+)""")


def main():
    fails = []
    # 1
    h = os.path.join(PUBLIC, "_headers")
    if not os.path.isfile(h) or open(h, encoding="utf-8").read() != security.headers_text():
        fails.append("_headers が無い、または security.py の出力と違う（generate_extra_pages.py を実行）")
    r = os.path.join(PUBLIC, "robots.txt")
    if not os.path.isfile(r) or "Disallow: /" not in open(r, encoding="utf-8").read():
        fails.append("robots.txt が無い")
    # 2〜4
    n = 0
    for dp, _, fns in os.walk(PUBLIC):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, PUBLIC)
            ext = os.path.splitext(fn)[1].lower()
            if ext in BAD_EXT or (ext == ".txt" and fn not in ALLOWED_TXT):
                fails.append("配布してはならない種類のファイル: " + rel)
                continue
            if ext not in (".html", ".js", ".css", ".json", ".webmanifest", ".svg"):
                continue
            n += 1
            s = open(p, encoding="utf-8", errors="replace").read()
            if ext in (".html", ".js", ".css", ".svg"):
                for m in EXT_URL.finditer(s):
                    host = m.group(2)
                    if host not in ALLOWED_HOSTS and host != "www.w3.org":
                        fails.append("許可していない外部ホストを読み込む: %s → %s" % (rel, host))
            for rx, label in SECRET:
                for m in rx.finditer(s):
                    fails.append("%s: %s「%s」" % (rel, label, m.group(0)[:50]))
    seen = set()
    for f in fails:
        if f not in seen:
            print("[FAIL]", f)
            seen.add(f)
    print("\n検査 %d ファイル / FAIL %d" % (n, len(seen)))
    sys.exit(1 if seen else 0)


if __name__ == "__main__":
    main()
