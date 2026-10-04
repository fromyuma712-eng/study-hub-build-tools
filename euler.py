# -*- coding: utf-8 -*-
"""分野と科目のオイラー図を組む（2026/10/4）。

    from euler import euler_figure
    html = euler_figure(C, manifest, current_key, semester_key)

- 分野を円、科目を点で描く。二つの分野にまたがる科目は、二つの円の重なりに置く。
- 円の位置と点の位置は、乱数を使わない計算で決める（同じ入力なら毎回同じ図）。ビルドの決定性を保つ。
- 円の大きさは科目数の平方根に比例する。燠火は「いま」だけ：今学期の科目の点。
- 科目名は長いので、図の中は科目の記号（code）にし、全科目の一覧を図の下に置く（記号と名前の対応、リンク）。
- 外部のライブラリ・サービスは使わない。

分野の付け方は site_config.py の SCOPE_TAGS（無ければ COURSE_TAGS）。個人の科目名はそちらにだけある。
"""
import math

from hub_style import esc

W_MIN, GAP = 40.0, 34.0        # 重なりの厚さの最小(px)・重ならない円どうしの最小の隙間
DOT_SPACE = 44.0               # 点どうしの最小の間隔
MARGIN = 14.0                  # 円の縁から点までの余白


def _tags(C):
    base = dict(getattr(C, "COURSE_TAGS", {}))
    base.update(getattr(C, "SCOPE_TAGS", {}))
    return base


def collect(C, manifest, current_key, semester_key):
    tags = _tags(C)
    skip = set(getattr(C, "SCOPE_NOT_CIRCLE", []))      # 円にしない分野（実習・基礎スキルなど科目の形式にあたるもの）
    order = [f for f in getattr(C, "FIELD_ORDER", []) if f not in skip]
    courses, others = [], []
    for it in manifest:
        name = it["course"]
        if name not in tags or not (it.get("src") or it.get("offline")):
            continue
        fields = [f for f in tags[name] if f in order]
        if not fields:
            others.append({"name": name, "code": it["code"], "kind": ", ".join(tags[name]),
                           "href": None if it.get("offline") else "../" + it["dest"].replace("/index.html", "/"),
                           "now": semester_key(it) == current_key, "offline": bool(it.get("offline"))})
            continue
        courses.append({
            "name": name, "code": it["code"], "fields": fields,
            "href": None if it.get("offline") else "../" + it["dest"].replace("/index.html", "/"),
            "now": semester_key(it) == current_key, "offline": bool(it.get("offline")),
        })
    used = [f for f in order if any(f in c["fields"] for c in courses)]
    return courses, used, others


def layout(courses, fields):
    n = {f: sum(1 for c in courses if f in c["fields"]) for f in fields}
    r = {f: 40.0 + 21.0 * math.sqrt(n[f]) for f in fields}
    shared = {}
    for c in courses:
        fs = c["fields"]
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                k = tuple(sorted((fs[i], fs[j])))
                shared[k] = shared.get(k, 0) + 1
    # 初期配置: 結びつきの強い順に、円周上へ並べる（乱数を使わない）
    deg = {f: sum(v for k, v in shared.items() if f in k) for f in fields}
    seq = sorted(fields, key=lambda f: (-deg[f], fields.index(f)))
    ring = []
    for f in seq:
        if not ring:
            ring.append(f)
            continue
        # 既に置いた中で最も結びつきの強い相手の隣へ入れる
        best = max(range(len(ring)), key=lambda i: (shared.get(tuple(sorted((f, ring[i]))), 0), -i))
        ring.insert(best + 1, f)
    R0 = 190.0 + 22.0 * len(fields)
    pos = {}
    for i, f in enumerate(ring):
        a = 2 * math.pi * i / len(ring) - math.pi / 2
        pos[f] = [R0 * math.cos(a), R0 * math.sin(a)]
    target = {}
    for i, a in enumerate(fields):
        for b in fields[i + 1:]:
            k = tuple(sorted((a, b)))
            s = shared.get(k, 0)
            if s:
                w = W_MIN + 14.0 * min(s - 1, 5)
                target[k] = (r[a] + r[b] - w, True)
            else:
                target[k] = (r[a] + r[b] + GAP, False)
    for it in range(1600):
        k_step = 0.10 if it < 1000 else 0.04
        force = {f: [0.0, 0.0] for f in fields}
        for i, a in enumerate(fields):
            for b in fields[i + 1:]:
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                d = math.hypot(dx, dy) or 0.01
                t, must = target[tuple(sorted((a, b)))]
                e = d - t
                if must or e < 0:
                    f_ = k_step * e * (1.0 if must else 1.6)
                    ux, uy = dx / d, dy / d
                    force[a][0] += f_ * ux; force[a][1] += f_ * uy
                    force[b][0] -= f_ * ux; force[b][1] -= f_ * uy
        for f in fields:
            force[f][0] -= 0.002 * pos[f][0]
            force[f][1] -= 0.002 * pos[f][1]
            pos[f][0] += force[f][0]
            pos[f][1] += force[f][1]
    return pos, r, n, shared


def place_dots(courses, fields, pos, r):
    placed = []
    items = sorted(courses, key=lambda c: (-len(c["fields"]), c["name"]))
    xs = [pos[f][0] for f in fields]; ys = [pos[f][1] for f in fields]
    x0, x1 = min(pos[f][0] - r[f] for f in fields), max(pos[f][0] + r[f] for f in fields)
    y0, y1 = min(pos[f][1] - r[f] for f in fields), max(pos[f][1] + r[f] for f in fields)
    step = 5.0
    for c in items:
        mem = c["fields"]
        cx = sum(pos[f][0] for f in mem) / len(mem)
        cy = sum(pos[f][1] for f in mem) / len(mem)
        best, best_p = None, None
        gx = x0
        while gx <= x1:
            gy = y0
            while gy <= y1:
                p = 0.0
                for f in fields:
                    d = math.hypot(gx - pos[f][0], gy - pos[f][1])
                    if f in mem:
                        over = d - (r[f] - MARGIN)
                        if over > 0:
                            p += over * over * 4.0
                    else:
                        over = (r[f] + MARGIN * 0.8) - d
                        if over > 0:
                            p += over * over * 8.0
                for q in placed:
                    d = math.hypot(gx - q[0], gy - q[1])
                    if d < DOT_SPACE:
                        p += (DOT_SPACE - d) ** 2 * 3.0
                p += 0.003 * ((gx - cx) ** 2 + (gy - cy) ** 2)   # 属する円の中心へ緩く引く
                if best_p is None or p < best_p - 1e-9:
                    best, best_p = (gx, gy), p
                gy += step
            gx += step
        c["xy"] = best
        placed.append(best)
    return placed


def violations(courses, pos, r):
    bad = []
    for c in courses:
        x, y = c["xy"]
        for f, (fx, fy) in pos.items():
            inside = math.hypot(x - fx, y - fy) <= r[f] - 4
            if (f in c["fields"]) != inside:
                bad.append((c["name"], f, "内にあるべき" if f in c["fields"] else "外にあるべき"))
    return bad


def label_spots(fields, pos, r, courses):
    out = {}
    dots = [c["xy"] for c in courses]
    for f in fields:
        best, best_s = None, -1e9
        for k in range(72):
            a = 2 * math.pi * k / 72
            ux, uy = math.cos(a), math.sin(a)
            bx, by = pos[f][0] + (r[f] + 6) * ux, pos[f][1] + (r[f] + 6) * uy
            s = 1e9
            for g in fields:
                if g == f:
                    continue
                s = min(s, math.hypot(bx - pos[g][0], by - pos[g][1]) - r[g])
            for q in dots:
                s = min(s, math.hypot(bx - q[0], by - q[1]) - 12)
            # 上や左右を少し優先（読みやすい位置）
            s += 6.0 * abs(ux) - 4.0 * max(0.0, uy)
            if s > best_s + 1e-9:
                best, best_s = (bx, by, ux, uy), s
        out[f] = best
    return out


def euler_figure(C, manifest, current_key, semester_key, report=False):
    courses, fields, others = collect(C, manifest, current_key, semester_key)
    if len(fields) < 2:
        return ""
    pos, r, n, shared = layout(courses, fields)
    place_dots(courses, fields, pos, r)
    bad = violations(courses, pos, r)
    if report:
        print("euler: %d 分野 / %d 科目 / 重なり違反 %d 件" % (len(fields), len(courses), len(bad)))
        for b in bad:
            print("   ", b)
    spots = label_spots(fields, pos, r, courses)

    pad_x, pad_top, pad_bot = 96.0, 40.0, 34.0
    def _lw(f):   # 分野名の描画幅(px)の見積もり（全角14px・半角8px）
        return sum(14.0 if ord(ch) > 0x2E7F else 8.0 for ch in f) + 10.0
    minx = min(min(pos[f][0] - r[f] for f in fields) - pad_x,
               min(spots[f][0] - (_lw(f) if spots[f][2] < -0.35 else (_lw(f) / 2 if abs(spots[f][2]) <= 0.35 else 0)) for f in fields) - 10)
    maxx = max(max(pos[f][0] + r[f] for f in fields) + pad_x * 0.4,
               max(spots[f][0] + (_lw(f) if spots[f][2] > 0.35 else (_lw(f) / 2 if abs(spots[f][2]) <= 0.35 else 0)) for f in fields) + 10)
    miny = min(pos[f][1] - r[f] for f in fields) - pad_top
    maxy = max(pos[f][1] + r[f] for f in fields) + pad_bot
    W, H = maxx - minx, maxy - miny
    tx = lambda x: x - minx
    ty = lambda y: y - miny
    fid = {f: i for i, f in enumerate(fields)}

    svg = ['<svg class="eu" viewBox="0 0 %.0f %.0f" role="img" aria-label="分野と科目のオイラー図。分野を円、科目を点で表し、複数の分野にまたがる科目は円の重なりに置く">' % (W, H)]
    for f in fields:
        svg.append('<circle class="fc" data-f="%d" cx="%.1f" cy="%.1f" r="%.1f" pathLength="1"/>'
                   % (fid[f], tx(pos[f][0]), ty(pos[f][1]), r[f]))
    for f in fields:
        bx, by, ux, uy = spots[f]
        anchor = "start" if ux > 0.35 else ("end" if ux < -0.35 else "middle")
        dy = 4 if abs(uy) < 0.5 else (14 if uy > 0 else -2)
        svg.append('<text class="fl" data-f="%d" x="%.1f" y="%.1f" text-anchor="%s" tabindex="0" role="button" '
                   'aria-label="%s のみ強調">%s</text>'
                   % (fid[f], tx(bx), ty(by) + dy, anchor, esc(f), esc(f)))
        svg.append('<text class="fn_" x="%.1f" y="%.1f" text-anchor="%s">%d</text>'
                   % (tx(bx), ty(by) + dy + 15, anchor, n[f]))
    for c in sorted(courses, key=lambda c: c["name"]):
        x, y = c["xy"]
        fl = " ".join(str(fid[f]) for f in c["fields"])
        cls = "dt" + (" now" if c["now"] else "") + (" off" if c["offline"] else "")
        inner = ('<circle class="dd" cx="%.1f" cy="%.1f" r="%s"/><text class="dl" x="%.1f" y="%.1f">%s</text>'
                 % (tx(x), ty(y), "4.5" if c["now"] else "4", tx(x) + 9, ty(y) + 4, esc(c["code"])))
        if c["href"]:
            svg.append('<a class="%s" href="%s" data-c="%s" data-f="%s"><title>%s</title>%s</a>'
                       % (cls, esc(c["href"]), esc(c["code"]), fl, esc(c["name"]), inner))
        else:
            svg.append('<g class="%s" data-c="%s" data-f="%s"><title>%s（非掲載）</title>%s</g>'
                       % (cls, esc(c["code"]), fl, esc(c["name"]), inner))
    svg.append("</svg>")

    leg = []
    for c in sorted(courses, key=lambda c: (not c["now"], c["code"])):
        tag = "a" if c["href"] else "div"
        href = ' href="%s"' % esc(c["href"]) if c["href"] else ""
        leg.append('<%s class="eli%s" data-c="%s"%s><span class="ec">%s</span><span class="en">%s</span>'
                   '<span class="ef">%s</span></%s>'
                   % (tag, " now" if c["now"] else "", esc(c["code"]), href, esc(c["code"]), esc(c["name"]),
                      " ∧ ".join(esc(f) for f in c["fields"]), tag))

    n_multi = sum(1 for c in courses if len(c["fields"]) > 1)
    out_html = ""
    if others:
        items_o = "".join(
            ('<%s class="oi%s"%s><span class="ec">%s</span><span class="en">%s</span><span class="ef">%s</span></%s>'
             % ("a" if o["href"] else "div", " now" if o["now"] else "",
                (' href="%s"' % esc(o["href"])) if o["href"] else "", esc(o["code"]), esc(o["name"]), esc(o["kind"]),
                "a" if o["href"] else "div"))
            for o in sorted(others, key=lambda o: (not o["now"], o["code"])))
        out_html = ('<div class="eo"><div class="eoh"><span class="lbl">OUTSIDE</span><span class="nm" style="font-size:14px;'
                    'color:var(--muted)">分野の円に入れない科目（実習・基礎スキルなど、科目の形式にあたるもの）</span></div>'
                    '<div class="elist">' + items_o + '</div></div>')
    body = (
        '<figure class="fig euler"><div class="fh"><span class="lbl">EULER</span>'
        '<span class="nm" style="font-size:14px;color:var(--muted)">分野と科目の重なり</span>'
        '<span class="rule"></span><span class="mt">%d 分野 ∧ %d 科目</span></div>' % (len(fields), len(courses))
        + "".join(svg)
        + '<p class="concl">分野を円、科目を点で表す。円の重なりにある %d 科目は、二つの分野にまたがる。'
          '<b>●</b> は今学期の科目。分野名を押すとその分野だけを強調する。</p>' % n_multi
        + '<div class="elist">' + "".join(leg) + '</div>' + out_html + '</figure>')
    return '<style>' + CSS + '</style><section class="sect" style="margin-top:0">' + body + '</section><script>' + JS + '</script>'


CSS = r"""
.fig.euler{max-width:none;margin:4px 0 30px}
.euler .eu{display:block;width:100%;height:auto;margin:8px 0 6px;overflow:visible}
.euler .fc{fill:none;stroke:var(--line-strong);stroke-width:1.2;transition:opacity .3s var(--settle),stroke .3s}
.euler .fl{font-size:14px;fill:var(--ink);cursor:pointer;font-family:var(--sans);transition:opacity .3s}
.euler .fl:hover,.euler .fl:focus{outline:none;text-decoration:underline;text-underline-offset:3px}
.euler .fn_{font-family:var(--mono);font-size:12px;fill:var(--faint);transition:opacity .3s}
.euler .dd{fill:var(--ground);stroke:var(--ink);stroke-width:1.2}
.euler .dl{font-family:var(--mono);font-size:12px;fill:var(--muted);letter-spacing:.04em}
.euler .dt.now .dd{fill:var(--ember);stroke:var(--ember)}
.euler .dt.now .dl{fill:var(--ember-text)}
.euler .dt.off .dd{stroke-dasharray:2 2}
.euler a.dt{cursor:pointer}
.euler a.dt:hover .dd,.euler a.dt:focus .dd,.euler .dt.hl .dd{stroke-width:2.4}
.euler .dt.hl .dl{fill:var(--ink)}
.euler .dt{transition:opacity .3s}
.euler[data-focus] .fc:not(.on),.euler[data-focus] .fl:not(.on),.euler[data-focus] .fn_:not(.on),.euler[data-focus] .dt:not(.on){opacity:.18}
.euler[data-focus] .fc.on{stroke:var(--ink);stroke-width:2}
.euler .elist{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:0 18px;margin-top:14px;border-top:1px solid var(--line)}
.euler .eo{margin-top:22px}.euler .eoh{display:flex;align-items:center;gap:10px;min-height:30px;flex-wrap:wrap}
.euler .oi{display:grid;grid-template-columns:4.4em 1fr;grid-template-rows:auto auto;column-gap:10px;min-height:46px;padding:6px 4px;border-bottom:1px solid var(--line);text-decoration:none;color:inherit}
.euler .oi.now .ec{color:var(--ember-text)}.euler .oi .ec{grid-row:1/3;align-self:center}
.euler .eli{display:grid;grid-template-columns:4.4em 1fr;grid-template-rows:auto auto;column-gap:10px;min-height:46px;padding:6px 4px;
  border-bottom:1px solid var(--line);text-decoration:none;color:inherit;transition:background-color .42s var(--settle)}
a.eli:hover,.eli.hl{background:var(--glow)}
.euler .ec{grid-row:1/3;font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--faint);align-self:center}
.euler .eli.now .ec{color:var(--ember-text)}
.euler .en{font-size:15px;line-height:1.4;color:var(--ink)}
.euler .ef{font-size:12px;color:var(--faint);line-height:1.4}
.js .euler .fc{stroke-dasharray:1;stroke-dashoffset:1}
.js .euler.grown .fc{stroke-dashoffset:0;transition:stroke-dashoffset 1.1s cubic-bezier(.2,.7,.2,1),opacity .3s var(--settle),stroke .3s}
.js .euler .dt,.js .euler .fl,.js .euler .fn_{opacity:0}
.js .euler.grown .dt,.js .euler.grown .fl,.js .euler.grown .fn_{opacity:1;transition:opacity .5s var(--settle) .5s}
.js .euler.grown svg[data-focus] .fc:not(.on),.js .euler.grown svg[data-focus] .fl:not(.on),.js .euler.grown svg[data-focus] .fn_:not(.on),
.js .euler.grown svg[data-focus] .dt:not(.on){opacity:.18;transition:opacity .3s var(--settle)}
.js .euler.grown svg[data-focus] .fc.on{stroke:var(--ink);stroke-width:2}
@media (prefers-reduced-motion:reduce){
  .js .euler .fc{stroke-dashoffset:0}.js .euler .dt,.js .euler .fl,.js .euler .fn_{opacity:1}
}
@media (max-width:560px){.euler .elist{grid-template-columns:1fr}.euler .dl{font-size:19px}.euler .fl{font-size:21px}.euler .fn_{font-size:17px}.euler .dd{stroke-width:1.6}.euler .fc{stroke-width:1.6}.euler .eu{margin:0 -6px 6px;width:calc(100% + 12px)}}
"""

JS = r"""
(function(){
  var fig=document.querySelector('.fig.euler'); if(!fig) return;
  var svg=fig.querySelector('svg.eu'), cur=null;
  /* 描画後の実際の幅で、はみ出す分野名の分だけ表示範囲を広げる（フォントの違いに左右されない） */
  function fit(){
    try{
      var vb=svg.viewBox.baseVal, x0=vb.x, x1=vb.x+vb.width, hit=false;
      svg.querySelectorAll('.fl,.fn_').forEach(function(t){
        var b=t.getBBox(); if(b.x<x0-1){x0=b.x-6;hit=true} if(b.x+b.width>x1+1){x1=b.x+b.width+6;hit=true}
      });
      if(hit) svg.setAttribute('viewBox',x0+' '+vb.y+' '+(x1-x0)+' '+vb.height);
    }catch(e){}
  }
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(fit); else fit();
  window.addEventListener('load',fit);
  function focus(f){
    cur=(cur===f)?null:f;
    if(cur===null){svg.removeAttribute('data-focus');svg.querySelectorAll('.on').forEach(function(e){e.classList.remove('on')});return}
    svg.setAttribute('data-focus',cur);
    svg.querySelectorAll('[data-f]').forEach(function(e){
      var on=e.getAttribute('data-f').split(' ').indexOf(String(cur))>=0; e.classList.toggle('on',on);
    });
  }
  svg.querySelectorAll('.fl').forEach(function(t){
    t.addEventListener('click',function(){focus(t.getAttribute('data-f'))});
    t.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();focus(t.getAttribute('data-f'))}});
  });
  /* 一覧と図の対応: 一覧に触れると、図の点を太くする */
  fig.querySelectorAll('.eli').forEach(function(li){
    var c=li.getAttribute('data-c'), d=svg.querySelector('.dt[data-c="'+c+'"]');
    function on(v){if(d)d.classList.toggle('hl',v);li.classList.toggle('hl',v)}
    li.addEventListener('mouseenter',function(){on(true)});li.addEventListener('mouseleave',function(){on(false)});
    li.addEventListener('focus',function(){on(true)});li.addEventListener('blur',function(){on(false)});
  });
  svg.querySelectorAll('.dt').forEach(function(d){
    var c=d.getAttribute('data-c'), li=fig.querySelector('.eli[data-c="'+c+'"]');
    d.addEventListener('mouseenter',function(){if(li)li.classList.add('hl')});
    d.addEventListener('mouseleave',function(){if(li)li.classList.remove('hl')});
  });
})();
"""
