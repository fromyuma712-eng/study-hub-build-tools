# -*- coding: utf-8 -*-
"""public/ の内部リンク（相対 href と #アンカー）が実在するかを調べる。外部リンクは見ない。
    python -X utf8 check_links.py
"""
import os
import re
import sys
from urllib.parse import unquote, urldefrag, urlparse

PUBLIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
HREF = re.compile(r'(?:href|src)="([^"]+)"')
ID = re.compile(r'\bid="([^"]+)"')


def target(base_file, url):
    p = urlparse(url)
    if p.scheme or url.startswith(("mailto:", "tel:", "data:", "javascript:", "//")):
        return None
    path = unquote(p.path)
    if not path:
        return base_file
    t = os.path.normpath(os.path.join(os.path.dirname(base_file), path)) if not path.startswith("/") else os.path.join(PUBLIC, path.lstrip("/"))
    if os.path.isdir(t):
        t = os.path.join(t, "index.html")
    return t


def main():
    ids = {}
    bad = []
    files = []
    for dp, _, fns in os.walk(PUBLIC):
        for n in fns:
            if n.endswith(".html"):
                files.append(os.path.join(dp, n))
    for f in files:
        s = open(f, encoding="utf-8").read()
        ids[f] = set(ID.findall(s))
    for f in files:
        s = open(f, encoding="utf-8").read()
        s = re.sub(r"<script.*?</script>", "", s, flags=re.S)
        for url in set(HREF.findall(s)):
            base, frag = urldefrag(url)
            t = target(f, url)
            if t is None:
                continue
            if not os.path.exists(t):
                bad.append((os.path.relpath(f, PUBLIC), url, "存在しない"))
            elif frag and t.endswith(".html") and unquote(frag) not in ids.get(t, set()):
                bad.append((os.path.relpath(f, PUBLIC), url, "アンカーなし"))
    for b in sorted(bad):
        print("%-34s %-40s %s" % b)
    print("\nHTML %d 頁 / 壊れたリンク %d 件" % (len(files), len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
