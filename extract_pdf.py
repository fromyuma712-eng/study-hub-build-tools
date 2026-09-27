# -*- coding: utf-8 -*-
"""講義資料（PDF・画像）を、執筆に使う文字と、目で見るべき頁の縮小一覧に分ける。

    python -X utf8 extract_pdf.py <PDFまたは画像> [...] [--out DIR] [--dpi 200] [--ocr-all] [--no-sheets]

頁ごとに次のように扱う（RUNBOOK §8）。
- 文字の層がある頁 … PyMuPDF でそのまま抜く（LLM のトークンを使わない）
- 文字の層が無い頁（写真・画像だけのスライド） … macOS の文字認識（vision_ocr）で起こす。
  LLM と違い読めない字を作らない。確信度の低い行には「〔?〕」を付ける
- 図・写真・表を含む頁 … 縮小一覧（6頁で1枚）にまとめる。**図の中身は文字にならないため、
  この一覧だけは画像として見る**（図を描き直す・図の説明を書くときに必要）

出力（既定は .extract/<資料名>/、.gitignore 済み）:
- text.txt     … 頁ごとの本文。見出し行に [層] / [OCR 確信度] / [図] の印
- sheets/*.png … 目で見るべき頁の縮小一覧
- summary.json … 頁ごとの判定と数え上げ
"""
import json
import os
import subprocess
import sys
import tempfile

import fitz

ROOT = os.path.dirname(os.path.abspath(__file__))
OCR_SRC = os.path.join(ROOT, "vision_ocr.swift")
OCR_BIN = os.path.join(ROOT, ".bin", "vision_ocr")

TEXT_MIN = 25          # これ未満の文字しか層に無い頁は画像だけの頁とみなし OCR にかける
FIG_IMAGE_RATIO = 0.12  # 画像が頁のこの割合以上を占めれば「図あり」
FIG_DRAWINGS = 25      # ベクトル図形（線・矩形）がこれ以上あれば「図あり」（表・図解）
LOW_CONF = 0.5         # 確信度がこれ以下の OCR 行に印を付ける
CLEAN_OCR = (5, 0.8)   # OCR が (行数, 平均確信度) 以上なら文字の画面写しとみなし、目で見る頁から外す
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff", ".gif", ".bmp")


def ocr_tool():
    """vision_ocr を用意する。ソースより古い・無いときだけ組み直す。"""
    if not os.path.exists(OCR_BIN) or os.path.getmtime(OCR_BIN) < os.path.getmtime(OCR_SRC):
        os.makedirs(os.path.dirname(OCR_BIN), exist_ok=True)
        subprocess.run(["swiftc", "-O", OCR_SRC, "-o", OCR_BIN], check=True)
    return OCR_BIN


def ocr(images):
    """画像の一覧を文字認識にかけ、{パス: [(文字, 確信度), ...]} を返す。"""
    if not images:
        return {}
    out = subprocess.run([ocr_tool()] + images, check=True, capture_output=True, text=True).stdout
    res = {}
    for line in out.splitlines():
        d = json.loads(line)
        if d.get("error"):
            raise RuntimeError("%s: %s" % (d["file"], d["error"]))
        res[d["file"]] = [(x["text"], x["conf"]) for x in d["lines"]]
    return res


def classify(page):
    """頁の文字の層・画像の占有率・ベクトル図形の数から、扱いを決める。"""
    text = page.get_text()
    area = abs(page.rect) or 1
    img = 0.0
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"]) & page.rect
        img += abs(r)
    ratio = min(1.0, img / area)
    drawings = len(page.get_drawings())
    return {
        "chars": len(text.strip()),
        "image_ratio": round(ratio, 3),
        "drawings": drawings,
        "ocr": len(text.strip()) < TEXT_MIN,
        "figure": ratio >= FIG_IMAGE_RATIO or drawings >= FIG_DRAWINGS,
    }, text


def _norm(text):
    return "".join(ch for ch in text if not ch.isspace() and not ch.isdigit() and ch != "〔" and ch != "〕" and ch != "?")


def look_pages(pages, texts, layers):
    """目で見るべき頁を選ぶ。

    - 図のある頁（画像・ベクトル図形）と、OCR で文字がほとんど取れなかった頁（写真・図だけの頁）
    - ただし OCR がきれいに読めた頁は文字の画面写しとみなして外す（図が無い限り）
    - 段階表示（同じ画像のまま文字を足していく連続スライド）は、最後の 1 枚だけ残す。
      今の頁の行の 9 割以上が次の頁にもあり、次の頁で画像が減っていなければ（同じか、部品が足された）、
      今の頁は途中の段である。画像が減る連続（写真を段階的に縮める等）は、違いそのものが内容なので残す
      （段ごとに行の並びが変わり、OCR の読みも少し揺れるため、行単位・9 割で判定する）
      比べる文字は、両頁に文字の層があれば層を使う（OCR は絵の中の字まで拾って揺れるため）
    """
    cand = []
    for p in pages:
        clean = p["ocr"] and p.get("ocr_lines", 0) >= CLEAN_OCR[0] and p.get("ocr_mean", 0) >= CLEAN_OCR[1]
        bare = p["ocr"] and p.get("ocr_lines", 0) < 3
        if (p["figure"] and not clean) or bare or (p["ocr"] and not clean):
            cand.append(p["page"])
    keep = []
    for n in cand:
        i = n - 1
        if i + 1 < len(pages):
            use = layers if _norm(layers[i]) and _norm(layers[i + 1]) else texts
            a = {_norm(x) for x in use[i].split("\n")} - {""}
            b = {_norm(x) for x in use[i + 1].split("\n")} - {""}
            grows = pages[i + 1]["image_ratio"] >= pages[i]["image_ratio"] - 0.01
            if grows and len(a & b) >= 0.9 * len(a):
                continue  # 途中の段。次の頁が同じ中身を含む
        keep.append(n)
    return keep


def contact_sheets(doc, pages, out_dir, cols=2, per=6, dpi=50):
    """目で見るべき頁を 6 頁ずつ 1 枚に並べる（頁番号を赤で入れる）。"""
    paths = []
    if not pages:
        return paths
    os.makedirs(out_dir, exist_ok=True)
    r = doc[pages[0] - 1].rect
    W, H = r.width, r.height
    for s in range(0, len(pages), per):
        chunk = pages[s:s + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = fitz.open()
        pg = sheet.new_page(width=W * cols, height=H * rows)
        for i, p in enumerate(chunk):
            x, y = (i % cols) * W, (i // cols) * H
            box = fitz.Rect(x, y, x + W, y + H)
            pg.show_pdf_page(box, doc, p - 1)
            pg.draw_rect(box, color=(1, 0, 0), width=2)
            pg.insert_text((x + 8, y + 22), "p%d" % p, fontsize=20, color=(1, 0, 0))
        path = os.path.join(out_dir, "sheet_%02d_p%d-%d.png" % (s // per + 1, chunk[0], chunk[-1]))
        pg.get_pixmap(dpi=dpi).save(path)
        paths.append(path)
    return paths


def extract(src, out_dir, dpi=200, ocr_all=False, sheets=True):
    is_image = src.lower().endswith(IMAGE_EXT)
    doc = fitz.open(src)
    if is_image:  # 画像はそのまま 1 頁の PDF として扱う
        doc = fitz.open("pdf", doc.convert_to_pdf())
    pages, texts = [], []
    for page in doc:
        info, text = classify(page)
        if is_image or ocr_all:
            info["ocr"] = True
        info["page"] = page.number + 1
        pages.append(info)
        texts.append(text)

    with tempfile.TemporaryDirectory() as tmp:
        todo = {}
        for info in pages:
            if info["ocr"]:
                path = os.path.join(tmp, "p%04d.png" % info["page"])
                doc[info["page"] - 1].get_pixmap(dpi=dpi).save(path)
                todo[info["page"]] = path
        found = ocr(list(todo.values()))

    body, n_low = [], 0
    for info, text in zip(pages, texts):
        tags = []
        if info["ocr"]:
            lines = found.get(todo[info["page"]], [])
            low = sum(1 for _, c in lines if c <= LOW_CONF)
            n_low += low
            mean = sum(c for _, c in lines) / len(lines) if lines else 0
            info.update(ocr_lines=len(lines), ocr_low=low, ocr_mean=round(mean, 2))
            tags.append("OCR 確信度%.2f" % mean if lines else "OCR 文字なし")
            text = "\n".join(("〔?〕" if c <= LOW_CONF else "") + t for t, c in lines)
        else:
            tags.append("層")
        if info["figure"]:
            tags.append("図")
        body.append("=== p%d [%s] ===\n%s" % (info["page"], " / ".join(tags), text.strip()))

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "text.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(body) + "\n")
    look = look_pages(pages, [b.split("\n", 1)[1] if "\n" in b else "" for b in body], texts)
    made = contact_sheets(doc, look, os.path.join(out_dir, "sheets")) if sheets else []
    summary = {
        "source": os.path.abspath(src), "pages": len(pages),
        "text_layer": sum(1 for p in pages if not p["ocr"]), "ocr": len(todo), "ocr_low_lines": n_low,
        "figure_pages": [p["page"] for p in pages if p["figure"]], "look_pages": look,
        "sheets": [os.path.relpath(x, out_dir) for x in made],
        "chars": sum(len(b) for b in body), "detail": pages,
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    return summary


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    base = opts[opts.index("--out") + 1] if "--out" in opts else os.path.join(ROOT, ".extract")
    dpi = int(opts[opts.index("--dpi") + 1]) if "--dpi" in opts else 200
    if "--out" in opts:
        args.remove(base)
    if "--dpi" in opts:
        args.remove(str(dpi))
    for src in args:
        name = os.path.splitext(os.path.basename(src))[0]
        out = os.path.join(base, name) if len(args) > 1 or "--out" not in opts else base
        s = extract(src, out, dpi=dpi, ocr_all="--ocr-all" in opts, sheets="--no-sheets" not in opts)
        print("%s: %d頁（層 %d・OCR %d、確信度の低い行 %d）／ %d字 ／ 目で見る頁 %d（一覧 %d枚）→ %s" % (
            name, s["pages"], s["text_layer"], s["ocr"], s["ocr_low_lines"], s["chars"],
            len(s["look_pages"]), len(s["sheets"]), out))


if __name__ == "__main__":
    main()
