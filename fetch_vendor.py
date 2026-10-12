# -*- coding: utf-8 -*-
"""MathJax・KaTeX・IBM Plex を、公式の npm パッケージ（版を固定）から vendor/ へ取り出す。

配信物（public/）は外部の配信網（CDN・Google Fonts）を読まず、自分のドメインの /vendor/ から読む。
これにより CSP の外部ホスト許可が要らなくなり、外部側の改変・停止・追跡の影響を受けない。
vendor/ は再取得できるため git には入れない（.gitignore）。

    python -X utf8 fetch_vendor.py
"""
import glob
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(ROOT, "vendor")
PKGS = ["mathjax@3.2.2", "katex@0.16.9", "@fontsource/ibm-plex-sans@5.3.0", "@fontsource/ibm-plex-mono@5.3.0"]
SANS_W = [300, 400, 500, 600, 700]
MONO_W = [400, 500]


def main():
    tmp = tempfile.mkdtemp()
    subprocess.run(["npm", "pack"] + PKGS, cwd=tmp, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ex = {}
    for t in glob.glob(os.path.join(tmp, "*.tgz")):
        d = t[:-4]
        os.makedirs(d)
        with tarfile.open(t) as tf:
            for m in tf.getmembers():
                if m.name.startswith("/") or ".." in m.name.split("/") or not (m.isfile() or m.isdir()):
                    raise SystemExit("不正なパッケージ内容: " + m.name)
            tf.extractall(d)
        ex[os.path.basename(d).rsplit("-", 1)[0]] = os.path.join(d, "package")
    shutil.rmtree(V, ignore_errors=True)
    # MathJax（chtml 出力。フォントは es5/output/chtml/fonts/woff-v2 を相対で読む）
    mj = os.path.join(V, "mathjax")
    src = os.path.join(ex["mathjax"], "es5")
    os.makedirs(os.path.join(mj, "output", "chtml", "fonts"))
    for n in ("tex-chtml.js", "tex-mml-chtml.js"):
        shutil.copy2(os.path.join(src, n), mj)
    shutil.copytree(os.path.join(src, "output", "chtml", "fonts", "woff-v2"), os.path.join(mj, "output", "chtml", "fonts", "woff-v2"))
    # autoload が必要に応じて読む TeX 拡張（boldsymbol・mhchem など）
    shutil.copytree(os.path.join(src, "input", "tex", "extensions"), os.path.join(mj, "input", "tex", "extensions"))
    shutil.copy2(os.path.join(ex["mathjax"], "LICENSE"), os.path.join(mj, "LICENSE"))
    # KaTeX
    kt = os.path.join(V, "katex")
    sd = os.path.join(ex["katex"], "dist")
    os.makedirs(os.path.join(kt, "fonts"))
    os.makedirs(os.path.join(kt, "contrib"))
    for n in ("katex.min.css", "katex.min.js"):
        shutil.copy2(os.path.join(sd, n), kt)
    shutil.copy2(os.path.join(sd, "contrib", "auto-render.min.js"), os.path.join(kt, "contrib"))
    for f in glob.glob(os.path.join(sd, "fonts", "*.woff2")):
        shutil.copy2(f, os.path.join(kt, "fonts"))
    shutil.copy2(os.path.join(ex["katex"], "LICENSE"), os.path.join(kt, "LICENSE"))
    # IBM Plex（OFL）。latin の woff2 だけ。和文は端末の書体を使う
    fd = os.path.join(V, "fonts")
    os.makedirs(fd)
    css = ["/* IBM Plex Sans / Mono (SIL OFL 1.1). 自前配信。fetch_vendor.py が生成 */"]
    for fam, key, ws in (("IBM Plex Sans", "fontsource-ibm-plex-sans", SANS_W), ("IBM Plex Mono", "fontsource-ibm-plex-mono", MONO_W)):
        slug = fam.lower().replace(" ", "-")
        for w in ws:
            fn = "%s-latin-%d-normal.woff2" % (slug, w)
            shutil.copy2(os.path.join(ex[key], "files", fn), fd)
            css.append('@font-face{font-family:"%s";font-style:normal;font-weight:%d;font-display:swap;src:url(%s) format("woff2")}' % (fam, w, fn))
        shutil.copy2(os.path.join(ex[key], "LICENSE"), os.path.join(fd, "LICENSE-" + slug))
    open(os.path.join(fd, "fonts.css"), "w", encoding="utf-8").write("\n".join(css) + "\n")
    shutil.rmtree(tmp, ignore_errors=True)
    n = sum(len(f) for _, _, f in os.walk(V))
    print("vendor/ に %d ファイルを置きました" % n)


if __name__ == "__main__":
    sys.exit(main())
