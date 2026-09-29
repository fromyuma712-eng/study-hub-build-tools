# -*- coding: utf-8 -*-
"""講義まとめの図（RUNBOOK §2-2）を組む部品。SVG の座標は手で書かず、ここの関数で計算して出す。

色は書かない。class（bx・ax・gr・ln・ln2・ar・ah・dot・em・emf・e・t）だけを付け、notes_skin.py の
`.o-fig` が明暗の表示に合わせて色を与える。燠火（em・emf・e）は注目の一点だけに使う。

    from figkit import T, box, arrow, fig, chart, text_width
    body = box(20, 40, 120, 44, '符号化') + arrow(142, 62, 200, 62)
    html = fig('xx1-model', 'MODEL', '通信のモデル', 740, 140, body, '結論を一行。', '通信のモデル')

図の id（data-fig）は「科目コード小文字＋回＋短い名」で頁の中で一意にする（例 cmp3-adder）。
"""
import html as _html
import math

FONT = {"t": 14.0, "": 12.0, "e": 12.0}   # class → 文字の大きさ(px)。t は和文 14px、それ以外は等幅 12px


def text_width(s, cls=""):
    """文字列の描画幅の見積もり（px）。全角は 1em、半角は 0.6em（等幅）/ 0.55em（和文書体）。"""
    size = FONT.get(cls, 12.0)
    w = 0.0
    for ch in s:
        if ord(ch) > 0x2E7F:          # CJK・全角
            w += size
        else:
            w += size * (0.55 if cls == "t" else 0.6)
    return w


def esc(s):
    return _html.escape(str(s), quote=False)


def T(x, y, s, cls="", anchor="middle"):
    """文字。cls='t' は箱の中の名前（和文14px）、'e' は注目（燠火の文字）、'' は目盛り・注記（等幅12px）。"""
    c = ' class="%s"' % cls if cls else ""
    return '<text%s x="%.1f" y="%.1f" text-anchor="%s">%s</text>' % (c, x, y, anchor, esc(s))


def box(x, y, w, h, label=None, cls="bx", sub=None):
    """箱。label は中央に和文14px。cls='em' は注目の箱。sub は箱の下に等幅の注記。"""
    o = '<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>' % (cls, x, y, w, h)
    if label:
        o += T(x + w / 2, y + h / 2 + 5, label, "t")
    if sub:
        o += T(x + w / 2, y + h + 18, sub)
    return o


def arrow(x1, y1, x2, y2, cls="ar", head="ah", draw=True):
    """矢印。draw=True なら画面に入ったとき描かれるように現れる（破線には使わない）。"""
    a = math.atan2(y2 - y1, x2 - x1)
    L = 7
    bx, by = x2 - L * math.cos(a), y2 - L * math.sin(a)
    p1 = (bx + 4 * math.sin(a), by - 4 * math.cos(a))
    p2 = (bx - 4 * math.sin(a), by + 4 * math.cos(a))
    pl = ' pathLength="1"' if draw else ""
    return ('<path class="%s"%s d="M%.1f %.1f L%.1f %.1f"/>' % (cls, pl, x1, y1, bx, by)
            + '<path class="%s" d="M%.1f %.1f L%.1f %.1f L%.1f %.1f Z"/>' % (head, x2, y2, p1[0], p1[1], p2[0], p2[1]))


def line(points, cls="ln", draw=True):
    """折れ線。points は [(x, y), ...]（SVG 座標）。"""
    pl = ' pathLength="1"' if draw and cls != "ln2" else ""
    return '<path class="%s"%s d="M%s"/>' % (cls, pl, " L".join("%.1f %.1f" % p for p in points))


def fig(fid, label, name, vw, vh, body, caption, aria):
    """図を1枚組む。label は欧文の札（MODEL・CHART・FLOW・TREE・PAIR・TIMELINE など）、name は和文の図名。
    caption は結論を一行（講義資料外の数値を使ったら冒頭に〔講義資料外の補足〕）。"""
    return ('<figure class="o-fig" data-fig="%s" role="img" aria-label="%s"><div class="o-fh">%s <b>%s</b></div>'
            '<svg viewBox="0 0 %d %d">%s</svg><figcaption>%s</figcaption></figure>'
            % (fid, esc(aria), label, esc(name), vw, vh, body, caption))


def fmt(v):
    return "%g" % v


def chart(W, H, L, B, xr, yr, xt, yt, xlab, ylab, series, extra=""):
    """L 字の軸を持つグラフ。L=左余白、B=下余白（46 以上にすると軸名が目盛りと重ならない）。
    xr/yr=値の範囲、xt/yt=目盛り（1・2・2.5・5・10 の倍数）、series=[(class, [(x,y) 値], 描く?)]。
    extra は X, Y（値→座標の関数）を受け取って SVG を返す関数でもよい（点・注記を足すとき）。"""
    (x0, x1), (y0, y1) = xr, yr
    X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - 16)
    Y = lambda v: H - B - (v - y0) / (y1 - y0) * (H - B - 18)
    o = ""
    for v in yt:
        o += '<path class="gr" d="M%d %.1f H%d"/>' % (L, Y(v), W - 16) + T(L - 8, Y(v) + 4, fmt(v), anchor="end")
    for v in xt:
        o += T(X(v), H - B + 18, fmt(v))
    o += '<path class="ax" d="M%d 10 V%d H%d"/>' % (L, H - B, W - 16)
    o += T(L, 12, ylab, anchor="start") + T(W - 16, H - 4, xlab, anchor="end")
    for cls, pts, draw in series:
        o += line([(X(a), Y(b)) for a, b in pts], cls, draw)
    return o + (extra(X, Y) if callable(extra) else extra)
