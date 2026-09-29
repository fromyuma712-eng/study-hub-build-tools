# -*- coding: utf-8 -*-
"""STUDY HUB の面（ハブ・分野別・ティア表）の意匠。

ObservatoryLauncher のデザイン総覧（~/Claude/08_ObservatoryLauncher/ObservatoryLauncher_デザイン総覧.md）
をサイトへ移したもの（2026/9/27）。要点:

- 地は鉄紺 #22303C、字は紙 #E7E4DE。燠火 #E4572E は「今まさに動いているもの」だけ（今学期・前回から更新された科目・
  面の頭の帯・標識灯）。本文に燠火を使うときは EmberText。
- 角を丸めない。影を使わない。面は塗らず、罫と格点で組む。背景は 24px の点格子。
- 大きさは 34/22/16/14/12px の五段だけ。数字は等幅。欧文は枠の名（札）、和文は中身。
- 小さな字は 6.5:1 以上（明るい表示では濃さを上げて同じ比を保つ）。
- 動きは役目のあるものだけ: rise（立ち上がり）・標識灯・沈み（押下）・桁送り（前回から変わった数）・
  伸び（図）・せり上がり（畳んだ節を開く）・溶け（表示切替・面の移動）・頁の印の移動。
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300..700&display=swap">')

CSS = r"""
:root{
  --ground:#22303C; --paper:#E7E4DE; --ember:#E4572E; --ember-text:#F69B7C;
  --ink:var(--paper);
  --muted:rgba(231,228,222,.85); --faint:rgba(231,228,222,.74); --ghost:rgba(231,228,222,.45);
  --line-strong:rgba(231,228,222,.55); --grid:rgba(231,228,222,.42); --line:rgba(231,228,222,.35);
  --dot:rgba(231,228,222,.16); --glow:rgba(231,228,222,.05);
  --sans:"IBM Plex Sans","Hiragino Sans","Noto Sans JP","Yu Gothic UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SF Mono","Hiragino Sans",monospace;
  --spring:cubic-bezier(.34,1.56,.64,1); --settle:cubic-bezier(.4,0,.2,1);
  color-scheme:dark;
}
/* 明るい表示: 地と字を入れ替え、小さな字の比（6.5:1 以上）を保つよう濃さを上げる */
:root[data-theme="light"]{
  --ground:#E7E4DE; --paper:#22303C; --ember-text:#882C10;
  --muted:rgba(34,48,60,.92); --faint:rgba(34,48,60,.86); --ghost:rgba(34,48,60,.5);
  --line-strong:rgba(34,48,60,.55); --grid:rgba(34,48,60,.34); --line:rgba(34,48,60,.28);
  --dot:rgba(34,48,60,.16); --glow:rgba(34,48,60,.05);
  color-scheme:light;
}
@view-transition{navigation:auto}
::view-transition-old(root),::view-transition-new(root){animation-duration:.36s}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--ground)}
body{
  background:var(--ground); color:var(--ink); font-family:var(--sans);
  font-size:16px; line-height:1.7; letter-spacing:.02em; padding:0 24px 96px;
  background-image:radial-gradient(var(--dot) 1px,transparent 1.2px); background-size:24px 24px;
  font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased;
  transition:background-color .36s var(--settle),color .36s var(--settle);
}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto}

/* ---- 面の頭 ---- */
.head{padding-top:0;margin-bottom:28px}
.band{width:12%;min-width:56px;height:3px;background:var(--ember)}
.headrow{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:8px 16px;margin-top:22px}
.id{display:flex;align-items:center;gap:12px}
.beacon{width:5px;height:5px;background:var(--ember);flex:none;animation:beacon 1.5s steps(1,end) infinite}
@keyframes beacon{0%{opacity:1}23.3%{opacity:.18}100%{opacity:.18}}
.face{white-space:nowrap;font-family:var(--mono);font-size:12px;font-weight:500;letter-spacing:.14em;color:var(--ink)}
.face i{font-style:normal;color:var(--faint)}
.nature{font-size:14px;color:var(--muted)}
.right{display:flex;align-items:center;gap:14px}
.tgl{
  white-space:nowrap;font-family:var(--mono);font-size:12px;letter-spacing:.1em;color:var(--faint);min-height:44px;
  background:none;border:1px solid var(--line);padding:0 14px;cursor:pointer;border-radius:0;
  transition:transform .42s var(--spring),border-color .2s,color .2s;
}
.tgl:hover{border-color:var(--line-strong);color:var(--ink)}
.tgl:active{transform:scale(.94);transition-duration:.07s}
.tag{font-size:14px;color:var(--faint);margin-top:10px}

/* 頁の印: 塗った四角が今の面。面を移ると四角が滑って移る（View Transitions） */
.pager{display:flex;gap:4px;margin-top:18px}
.pg{
  display:flex;align-items:center;gap:8px;min-height:44px;padding:0 12px 0 0;text-decoration:none;
  font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--faint);
  transition:transform .42s var(--spring),color .2s;
}
.pg .sq{width:9px;height:9px;border:1px solid var(--line-strong);flex:none}
.pg.on{color:var(--ink)}
.pg.on .sq{background:var(--ink);border-color:var(--ink);view-transition-name:pager-mark}
.pg:hover{color:var(--ink)}
.pg:active{transform:scale(.94);transition-duration:.07s}
::view-transition-group(pager-mark){animation-duration:.38s;animation-timing-function:cubic-bezier(.3,1.3,.5,1)}

/* 弦材: 上下二本の罫を格点で結ぶ。面に一箇所だけ（諸元の帯） */
.truss{
  position:relative;min-height:46px;display:flex;flex-wrap:wrap;align-items:center;column-gap:.9em;row-gap:0;margin:0 0 40px;padding:8px 2px!important;
  border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);
  font-family:var(--mono);font-size:12px;letter-spacing:.1em;color:var(--faint);padding:0 2px;
}
.truss::before,.truss::after{
  content:"";position:absolute;left:0;right:0;height:5px;pointer-events:none;
  background:linear-gradient(90deg,var(--line-strong) 0 5px,transparent 5px 120px) 0 0/120px 5px repeat-x;
}
.truss::before{top:-3px}.truss::after{bottom:-3px}
.truss b{color:var(--ink);font-weight:500}
.sp{white-space:nowrap}
.sp+.sp::before{content:"\2227";margin-right:.9em;color:var(--faint)}
.roll{display:inline-block;height:1.2em;line-height:1.2em;overflow:hidden;vertical-align:bottom}
.roll>span{display:block;animation:roll .38s cubic-bezier(.4,0,.2,1) both}
@keyframes roll{from{transform:translateY(0)}to{transform:translateY(-50%)}}

/* ---- 節 ---- */
.sect{margin-top:12px;scroll-margin-top:20px}
.sect>summary{list-style:none;cursor:pointer}
.sect>summary::-webkit-details-marker{display:none}
.sh{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px;min-height:46px;padding:4px 0}
.anc{width:5px;height:5px;background:var(--line-strong);flex:none}
.lbl{font-family:var(--mono);font-size:12px;font-weight:500;letter-spacing:.14em;color:var(--faint);flex:none}
.nm{font-size:16px;color:var(--ink);flex:0 1 auto;min-width:0;line-height:1.5}
.rule{flex:1;height:1px;background:var(--line);min-width:16px}
.mt{font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--faint);flex:none}
.chev{width:9px;height:9px;border-right:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);
  transform:rotate(45deg) translate(-2px,-2px);transition:transform .3s var(--settle);flex:none;margin-left:2px}
details[open]>summary .chev{transform:rotate(225deg) translate(-2px,-2px)}
summary:hover .nm{color:var(--ink)} summary:hover .rule{background:var(--line-strong)}
.sect.now>summary .anc{background:var(--ember)}
.sect.now>summary .lbl{color:var(--ember-text)}
/* 今学期だけ Hero（34px）で名乗る。面で一つだけ */
.sect.now>summary .nm{font-size:34px;font-weight:600;letter-spacing:-.02em;line-height:1.25}
.sect.now>summary .sh{min-height:64px;flex-wrap:wrap}
.warn>summary .anc{background:var(--ember)} .warn>summary .lbl{color:var(--ember-text)}
.body{padding:6px 0 28px}
.note{font-size:14px;color:var(--muted);margin:0 0 16px;max-width:820px}
.note b{color:var(--ink);font-weight:500}

/* ---- 札（カード）: 塗らず、罫と四隅の格点で組む ---- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;align-items:stretch}
.card{
  position:relative;border:1px solid var(--line);padding:16px 18px 14px;display:flex;flex-direction:column;
  text-decoration:none;color:inherit;min-height:44px;background:transparent;
  transition:transform .42s var(--spring),background-color .42s var(--settle),border-color .2s;
}
.card::before,.card::after,.card .bl,.card .br{content:"";position:absolute;width:5px;height:5px;background:var(--line-strong);pointer-events:none}
.card::before{top:-3px;left:-3px}.card::after{top:-3px;right:-3px}
.card .bl{bottom:-3px;left:-3px}.card .br{bottom:-3px;right:-3px}
a.card:hover{border-color:var(--line-strong)}
a.card:active{transform:scale(.985);background-color:var(--glow);transition-duration:.07s}
.card.fresh::before{background:var(--ember)}
.k{font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--faint);display:flex;gap:10px;align-items:center}
.k .new{color:var(--ember-text);display:none}
.card.fresh .k .new{display:inline}
.crs{font-size:16px;font-weight:400;color:var(--ink);margin:6px 0 2px;line-height:1.5}
.ttl{font-size:14px;color:var(--muted)}
.dsc{font-size:14px;color:var(--faint);flex:1;margin-top:6px;line-height:1.65}
.meta{font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--faint);margin-top:12px;padding-top:9px;border-top:1px solid var(--line)}
.miss{opacity:.6}
.card.offline{border-style:dashed}
.card.offline .crs{color:var(--muted)}

/* ---- 行（台帳）: 名前が縦に並ぶ所。一行 46px ---- */
.rows{border-top:1px solid var(--line)}
.row{display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:16px;align-items:center;min-height:46px;
  padding:8px 4px;border-bottom:1px solid var(--line);text-decoration:none;color:inherit;
  transition:transform .42s var(--spring),background-color .42s var(--settle)}
.row:hover{background:var(--glow)}
.row:active{transform:scale(.985);background:var(--glow);transition-duration:.07s}
.row .rc{font-size:14px;color:var(--faint)}
.row .rt{font-size:16px;color:var(--ink)}
@media (max-width:560px){.row{grid-template-columns:1fr;gap:0}}

/* ---- 図: 面で塗らず細い罫で立てる。L 字の軸。伸びて現れる ---- */
.fig{margin:4px 0 22px;max-width:820px}
.fig .fh{display:flex;align-items:center;gap:12px;min-height:30px}
.fig .fr{display:grid;grid-template-columns:minmax(120px,210px) 1fr 5.5em;align-items:center;gap:12px;min-height:30px}
.fig .fn{font-size:14px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fig .fv{font-family:var(--mono);font-size:12px;color:var(--faint);text-align:right}
.fig .track{position:relative;height:30px;
  background:linear-gradient(90deg,var(--grid) 0 1px,transparent 1px) 0 0/calc(100%/7) 100% repeat-x;
  border-left:1px solid var(--line-strong);border-right:1px solid var(--grid)}
.fig .bar{position:absolute;left:0;top:13px;height:3px;background:var(--muted);transform-origin:left center}
.fig .bar::after{content:"";position:absolute;right:-2px;top:-1px;width:5px;height:5px;background:var(--ember)}
.fig .axis{display:grid;grid-template-columns:minmax(120px,210px) 1fr 5.5em;gap:12px}
.fig .ticks{position:relative;height:22px;border-top:1px solid var(--line-strong)}
.fig .ticks span{position:absolute;top:3px;transform:translateX(-50%);font-family:var(--mono);font-size:12px;color:var(--faint)}
.fig .unit{font-family:var(--mono);font-size:12px;color:var(--faint)}
.fig .concl{font-size:14px;color:var(--muted);margin-top:6px}

footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);font-size:14px;color:var(--faint)}

/* ---- 動き ---- */
.js .rise{opacity:0;transform:translateY(4px)}
.js .rise.in{opacity:1;transform:none;transition:opacity .2s var(--settle),transform .2s var(--settle);transition-delay:var(--d,0ms)}
.js .fig .bar{transform:scaleX(0)}
.js .fig.grown .bar{transform:scaleX(1);transition:transform .65s cubic-bezier(.2,.7,.2,1)}
details.opening .body>*{animation:lift .42s var(--spring) both}
@keyframes lift{from{opacity:0;transform:translateY(56px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .js .rise{opacity:1;transform:none}.js .fig .bar{transform:none}
}
@media (max-width:560px){
  body{padding:0 16px 72px}
  .nature{display:none}
  .sect.now>summary .sh{row-gap:0}
  .sect.now>summary .nm{font-size:22px;flex-basis:100%;order:0}
  .grid{grid-template-columns:1fr}
  .fig .fr{grid-template-columns:1fr 4.5em;row-gap:0}
  .fig .fn{grid-column:1/-1}
  .fig .axis{grid-template-columns:1fr 4.5em}
  .fig .axis>div:first-child{display:none}
}
"""

JS = r"""
(function(){
  var D=document.documentElement; D.classList.add('js');
  function get(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function set(k,v){try{localStorage.setItem(k,v)}catch(e){}}

  /* 表示切替: 既定は鉄紺（地の色は変えない）。明るい表示は本人が選んだときだけ */
  var TK='studyhub_theme', b=document.getElementById('tgl');
  function cur(){return D.getAttribute('data-theme')==='light'?'light':'dark'}
  var s=get(TK); if(s==='light') D.setAttribute('data-theme','light');
  function paint(){ if(b) b.textContent = cur()==='dark' ? 'LIGHT ∨ [DARK]' : '[LIGHT] ∨ DARK'; }
  if(b) b.addEventListener('click',function(){
    if(cur()==='dark'){D.setAttribute('data-theme','light');set(TK,'light')}
    else{D.removeAttribute('data-theme');set(TK,'dark')}
    paint();
  });
  paint();

  /* 前回の訪問から更新された札に燠火の格点と NEW を付ける（変わったことに気付かせる） */
  var face=document.body.getAttribute('data-face')||'hub';
  var VK='studyhub_seen_'+face, prev=parseInt(get(VK)||'0',10), now=Date.now();
  var week=7*864e5;
  document.querySelectorAll('[data-mtime]').forEach(function(el){
    var m=parseInt(el.getAttribute('data-mtime'),10)*1000;
    if(prev ? m>prev : now-m<week) el.classList.add('fresh');
  });
  set(VK,String(now));

  /* 桁送り: 前回と数が変わった桁だけが下から上へ回る（380ms） */
  document.querySelectorAll('[data-count]').forEach(function(el){
    var key='studyhub_count_'+el.getAttribute('data-count'), n=el.textContent, old=get(key);
    set(key,n);
    if(old===null||old===n) return;
    var a=old.split(''), c=n.split(''), L=Math.max(a.length,c.length);
    while(a.length<L)a.unshift(' '); while(c.length<L)c.unshift(' ');
    el.textContent='';
    for(var i=0;i<L;i++){
      if(a[i]===c[i]){el.appendChild(document.createTextNode(c[i]));continue}
      var r=document.createElement('span');r.className='roll';
      var inner=document.createElement('span');inner.innerHTML=(a[i]===' '?'&nbsp;':a[i])+'<br>'+c[i];
      r.appendChild(inner);el.appendChild(r);
    }
  });

  /* 畳んだ節の開閉を覚える。開いたときは中身がせり上がる */
  document.querySelectorAll('details.sect[id]').forEach(function(d){
    var k='studyhub_open_'+face+'_'+d.id, v=get(k);
    if(v==='1') d.open=true; else if(v==='0') d.open=false;
    d.addEventListener('toggle',function(){
      set(k,d.open?'1':'0');
      if(d.open){d.classList.add('opening');setTimeout(function(){d.classList.remove('opening')},700);reveal(d)}
    });
  });

  /* rise: 面に来たものが立ち上がる（200ms・4px）。図は根元から伸びる（最初の一度だけ） */
  var io=('IntersectionObserver' in window)?new IntersectionObserver(function(es){
    var k=0;
    es.forEach(function(e){
      if(!e.isIntersecting) return;
      var t=e.target; io.unobserve(t);
      if(t.classList.contains('fig')){t.classList.add('grown');return}
      t.style.setProperty('--d',Math.min(k++*24,240)+'ms'); t.classList.add('in');
    });
  },{rootMargin:'0px 0px -4% 0px'}):null;
  function reveal(root){
    root.querySelectorAll('.rise:not(.in),.fig:not(.grown)').forEach(function(el){
      if(io) io.observe(el); else el.classList.add(el.classList.contains('fig')?'grown':'in');
    });
  }
  reveal(document);
  /* 安全策: 描画が止まっている等で観測が届かなくても、画面内の要素は必ず見せる */
  setTimeout(function(){
    document.querySelectorAll('.rise:not(.in),.fig:not(.grown)').forEach(function(el){
      var r=el.getBoundingClientRect();
      if(r.height&&r.top<innerHeight&&r.bottom>0) el.classList.add(el.classList.contains('fig')?'grown':'in');
    });
  },1200);
})();
"""

FACES = [("hub", "HUB", "", "科目から"), ("fields", "FIELDS", "fields/", "分野から"), ("tier", "TIER", "tier/", "評価から")]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def sect_head(label, name, meta="", chevron=False):
    """節の見出し: 格点 → 札 → 名 → 罫 → 右肩のメタ。"""
    return ("<div class=\"sh\"><span class=\"anc\"></span><span class=\"lbl\">" + esc(label) + "</span>"
            "<span class=\"nm\">" + esc(name) + "</span><span class=\"rule\"></span>"
            + ("<span class=\"mt\">" + meta + "</span>" if meta else "")
            + ("<span class=\"chev\"></span>" if chevron else "") + "</div>")


def page(body, spec, face="hub"):
    """面を一枚組む。face は hub / fields / tier。"""
    idx = [f[0] for f in FACES].index(face)
    up = "" if face == "hub" else "../"
    pager = "".join(
        "<a class=\"pg" + (" on" if i == idx else "") + "\" href=\"" + (up + href if href else (up or "./")) + "\""
        + (" aria-current=\"page\"" if i == idx else "") + "><span class=\"sq\"></span>" + lab + "</a>"
        for i, (_, lab, href, _n) in enumerate(FACES))
    return ("<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"robots\" content=\"noindex,nofollow\"><meta name=\"theme-color\" content=\"#22303C\">"
            "<title>STUDY HUB</title>" + FONTS + "<style>" + CSS + "</style>"
            "<script>try{if(localStorage.getItem('studyhub_theme')==='light')"
            "document.documentElement.setAttribute('data-theme','light')}catch(e){}</script>"
            "</head><body data-face=\"" + face + "\"><div class=\"wrap\">"
            "<header class=\"head\"><div class=\"band\"></div><div class=\"headrow\">"
            "<div class=\"id\"><span class=\"beacon\"></span><span class=\"face\">STUDY HUB <i>∧</i> "
            + FACES[idx][1] + " " + "%02d/%02d" % (idx + 1, len(FACES)) + "</span></div>"
            "<div class=\"right\"><span class=\"nature\">" + FACES[idx][3] + "</span>"
            "<button class=\"tgl\" id=\"tgl\">LIGHT ∨ DARK</button></div></div>"
            "<p class=\"tag\">型は借りる。署名は残す。</p>"
            "<nav class=\"pager\">" + pager + "</nav></header>"
            "<div class=\"truss\">" + spec + "</div>" + body +
            "<footer>個人利用専用。認証により本人のみ到達可能。"
            "更新は build.py ∧ wrangler pages deploy による。</footer>"
            "</div><script>" + JS + "</script></body></html>")
