# -*- coding: utf-8 -*-
"""科目の中身のページ（原本HTML）へ OBSERVATORY の意匠を差し込む。

ハブ（hub_style.py）と同じ体系を、各科目の中身のページへ広げる（2026/9/27 本人指示）。
原本の既存 CSS は消さず、その後ろに上書きの層を置く。差し込む箇所は目印で囲み、何度実行しても
同じ結果になる（既存の層を外してから入れ直す）。層を外せば原本に戻る。

    python -X utf8 notes_skin.py          # 適用（変更した頁の数を表示）
    python -X utf8 notes_skin.py --check  # 適用漏れ・古い層の有無だけを調べる（書き込まない）

頁の種類:
- notes … 講義まとめの共通雛形（色変数 --ctx-bar を持つ）。面の頭・回の索引・読んだ位置の線・rise を足す
- quiz / workbook / sheet … 独自の設計を持つアプリ（問題集・学習帳・数式の一覧表）。どの頁がどれかは
  site_config.py（非公開）の APP_KINDS が決める。色変数の付け替えと面の頭だけを足し、アプリ自身の動き・索引・進捗表示はそのまま使う

差し込むもの:
- <head> の末尾: 書体・上書きの CSS・既定の表示（鉄紺）を決める小さな script
- <body> の直後: 面の頭（燠火の帯・STUDY HUB へ戻る・科目の札）。notes は回の索引も
- </body> の直前: 動き・表示切替の同期

印刷は原本の印刷用 CSS のままにする（上書きは画面だけに効かせる）。
"""
import importlib.util
import os
import re
import sys

import atomicio
from hub_style import FONTS, esc
from siteconf import C

ROOT = os.path.dirname(os.path.abspath(__file__))
MARK = "OBSERVATORY-SKIN"
VERSION = "5"

SANS = '"IBM Plex Sans","Hiragino Sans","Noto Sans JP","Yu Gothic UI",sans-serif'
MONO = '"IBM Plex Mono",ui-monospace,"SF Mono","Hiragino Sans",monospace'
SPRING = "cubic-bezier(.34,1.56,.64,1)"
SETTLE = "cubic-bezier(.4,0,.2,1)"

# ---- 全頁に共通: 色の体系・面の頭 ----
# 正解・不正解の緑と赤は意味を担う色なので残し、燠火の文字と同じく 6.5:1 以上の濃さに揃える。
BASE_CSS = r"""
@view-transition{navigation:auto}
::view-transition-old(root),::view-transition-new(root){animation-duration:.36s}
@media screen{
:root:not([data-theme="light"]){
  --o-ground:#22303C; --o-paper:#E7E4DE; --o-ember:#E4572E; --o-ember-text:#F69B7C;
  --o-muted:rgba(231,228,222,.85); --o-faint:rgba(231,228,222,.74);
  --o-ls:rgba(231,228,222,.55); --o-line:rgba(231,228,222,.35); --o-dot:rgba(231,228,222,.16); --o-glow:rgba(231,228,222,.06);
  --o-good:#8FCBA0; --o-good-bg:rgba(143,203,160,.12); --o-bad:#EBA894; --o-bad-bg:rgba(235,168,148,.12);
  color-scheme:dark;
}
:root[data-theme="light"]{
  --o-ground:#E7E4DE; --o-paper:#22303C; --o-ember:#E4572E; --o-ember-text:#882C10;
  --o-muted:rgba(34,48,60,.92); --o-faint:rgba(34,48,60,.86);
  --o-ls:rgba(34,48,60,.55); --o-line:rgba(34,48,60,.28); --o-dot:rgba(34,48,60,.16); --o-glow:rgba(34,48,60,.06);
  --o-good:#164D2A; --o-good-bg:rgba(22,77,42,.1); --o-bad:#7F2616; --o-bad-bg:rgba(127,38,22,.1);
  color-scheme:light;
}
html{background:var(--o-ground)}
/* 面の頭: 燠火の帯（幅12%）・戻る・科目の札 */
.o-head{max-width:980px;margin:0 auto 6px}
.o-band{width:12%;min-width:56px;height:3px;background:var(--o-ember)}
.o-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px 18px;min-height:46px;margin-top:14px}
.o-back{display:inline-flex;align-items:center;gap:10px;min-height:44px;text-decoration:none;color:var(--o-paper);
  font-family:""" + MONO + r""";font-size:12px;font-weight:500;letter-spacing:.14em;transition:transform .42s """ + SPRING + r"""}
.o-back:active{transform:scale(.94);transition-duration:.07s}
.o-back .o-arrow{width:9px;height:9px;border-left:1px solid var(--o-ls);border-bottom:1px solid var(--o-ls);transform:rotate(45deg);margin:0 2px 0 3px;transition:transform .3s}
.o-back:hover .o-arrow{transform:translateX(-3px) rotate(45deg)}
.o-face{font-family:""" + MONO + r""";font-size:12px;letter-spacing:.14em;color:var(--o-faint);white-space:nowrap}
.o-face i{font-style:normal;margin:0 .5em}
.o-beacon{width:5px;height:5px;background:var(--o-ember);flex:none;animation:o-beacon 1.5s steps(1,end) infinite}
@keyframes o-beacon{0%{opacity:1}23.3%{opacity:.18}100%{opacity:.18}}
@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
}
"""

# 四隅の格点（罫の角に 5px の四角）。面は塗らない
CORNERS = ("linear-gradient(var(--o-ls),var(--o-ls)) left top/5px 5px no-repeat,"
           "linear-gradient(var(--o-ls),var(--o-ls)) right top/5px 5px no-repeat,"
           "linear-gradient(var(--o-ls),var(--o-ls)) left bottom/5px 5px no-repeat,"
           "linear-gradient(var(--o-ls),var(--o-ls)) right bottom/5px 5px no-repeat")

# ---- 講義まとめ（共通雛形） ----
NOTES_CSS = r"""
@media screen{
:root:not([data-theme="light"]),:root[data-theme="light"]{
  --paper:var(--o-ground); --panel:transparent; --ink:var(--o-paper); --sub:var(--o-muted);
  --line:var(--o-line); --accent:var(--o-ember); --band:transparent; --ctx:transparent; --ctx-bar:var(--o-ls);
  --th:var(--o-glow); --note:transparent; --note-bd:var(--o-line);
}
html{scroll-behavior:smooth}
body{
  font-family:""" + SANS + r""";
  background:var(--o-ground); color:var(--o-paper); font-size:16px; line-height:1.85; letter-spacing:.02em;
  padding:0 24px 96px; font-variant-numeric:tabular-nums; -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(var(--o-dot) 1px,transparent 1.2px); background-size:24px 24px;
  transition:background-color .36s """ + SETTLE + r""",color .36s """ + SETTLE + r""";
}
.wrap{max-width:980px}
.o-row{padding-right:170px}
h1{font-size:34px;font-weight:600;letter-spacing:-.02em;line-height:1.3;border-bottom:none;padding:0;margin:14px 0 8px}
.meta{font-size:14px;color:var(--o-muted);margin-bottom:28px}
h2{position:relative;font-size:22px;font-weight:500;letter-spacing:-.01em;line-height:1.45;
  border-left:none;padding:0 0 .35em 17px;margin:2.2em 0 .5em;border-bottom:1px solid var(--o-line);scroll-margin-top:80px}
h2::before{content:"";position:absolute;left:0;top:.62em;width:5px;height:5px;background:var(--o-ls);transition:background-color .3s}
h2.o-now::before{background:var(--o-ember)}
h3{font-size:14px;font-weight:500;color:var(--o-faint);letter-spacing:.04em;margin:1.2em 0 .4em}
h3::before{content:"";display:inline-block;width:12px;height:1px;background:var(--o-ls);vertical-align:middle;margin-right:8px}
.block,.qblock{position:relative;background:none;border:1px solid var(--o-line);border-radius:0;padding:14px 18px}
.block::before,.qblock::before{content:"";position:absolute;inset:-3px;pointer-events:none;background:""" + CORNERS + r"""}
.pt{background:none;border-left:1px solid var(--o-ls);padding:.45em .9em;font-size:16px;line-height:1.85}
.pt b,.ex b,.timeline b,.block b{color:var(--o-paper);font-weight:600}
.term{font-family:""" + MONO + r""";font-size:12px;letter-spacing:.06em;
  background:none;border:1px solid var(--o-line);border-radius:0;color:var(--o-muted);padding:.05em .5em}
.ex{background:none;border:1px solid var(--o-line);border-radius:0;font-size:15px}
.formula,.context{background:none;border-left:1px solid var(--o-ls);border-radius:0}
.instructions{background:none;border:1px solid var(--o-line);border-radius:0}
.note{background:none;border:1px solid var(--o-line);color:var(--o-faint);font-size:14px}
.small{color:var(--o-faint);font-size:14px}
.pt .small{font-size:inherit}
code{font-family:""" + MONO + r""";font-size:.88em;color:var(--o-paper)}
table{border-color:var(--o-line)}
th{background:transparent;color:var(--o-muted);font-weight:500}
th,td{border-color:var(--o-line)!important}
hr{border:none;border-top:1px solid var(--o-line)}
mjx-container{color:var(--o-paper)}
.tgl{position:absolute;top:14px;right:24px;font-family:""" + MONO + r""";font-size:12px;letter-spacing:.1em;
  color:var(--o-faint);background:var(--o-ground);border:1px solid var(--o-line);border-radius:0;min-height:44px;padding:0 14px;
  transition:transform .42s """ + SPRING + r""",border-color .2s,color .2s}
.tgl:hover{border-color:var(--o-ls);color:var(--o-paper)}
.tgl:active{transform:scale(.94);transition-duration:.07s}
/* 回の索引は画面上部に留まり、今読んでいる回を示し続ける */
.o-toc{position:sticky;top:0;z-index:10;max-width:980px;margin:10px auto 0;display:flex;flex-wrap:wrap;gap:4px;
  background:var(--o-ground);border-top:1px solid var(--o-ls);border-bottom:1px solid var(--o-ls);padding:4px 0}
.o-toc:empty{display:none}
.o-toc a{position:relative;display:flex;align-items:center;justify-content:center;min-width:44px;min-height:44px;
  text-decoration:none;font-family:""" + MONO + r""";font-size:12px;letter-spacing:.06em;color:var(--o-faint);
  border:1px solid transparent;transition:transform .42s """ + SPRING + r""",color .2s,border-color .2s}
.o-toc a:hover{border-color:var(--o-line);color:var(--o-paper)}
.o-toc a:active{transform:scale(.94);transition-duration:.07s}
.o-toc a.on{color:var(--o-paper);border-color:var(--o-line)}
.o-toc a.on::after{content:"";position:absolute;top:-3px;left:-3px;width:5px;height:5px;background:var(--o-ember)}
.o-toc .o-lbl{display:flex;align-items:center;padding:0 10px 0 2px;font-family:""" + MONO + r""";
  font-size:12px;letter-spacing:.14em;color:var(--o-faint)}
/* 読んだ位置の線（今の位置だけ燠火） */
.o-progress{position:fixed;left:0;top:0;height:2px;width:100%;background:var(--o-ember);transform-origin:left center;
  transform:scaleX(0);z-index:20;pointer-events:none}
/* 図（2026/9/27 本人指示「理解のしやすさを主に」）: 面で塗らず細い罫で描く。L 字の軸と単位、
   燠火は注目の一点だけ、図の下に結論を一行。SVG の部品は class で色を受け取るので明暗の切替に追従する */
.o-fig{position:relative;margin:14px 0 18px;padding:14px 16px 12px;border:1px solid var(--o-line)}
.o-fig::before{content:"";position:absolute;inset:-3px;pointer-events:none;background:""" + CORNERS + r"""}
.o-fig .o-fh{display:flex;align-items:center;gap:10px;margin-bottom:10px;font-family:""" + MONO + r""";font-size:12px;letter-spacing:.14em;color:var(--o-faint)}
.o-fig .o-fh b{font-family:""" + SANS + r""";font-size:14px;letter-spacing:.02em;font-weight:500;color:var(--o-paper)}
.o-fig svg{display:block;width:100%;height:auto;max-width:760px;margin:0 auto;overflow:visible}
.o-fig svg text{fill:var(--o-faint);font-family:""" + MONO + r""";font-size:12px}
.o-fig svg text.t{fill:var(--o-paper);font-family:""" + SANS + r""";font-size:14px}
.o-fig svg text.e{fill:var(--o-ember-text)}
.o-fig svg .ax{stroke:var(--o-ls);stroke-width:1;fill:none}
.o-fig svg .gr{stroke:var(--o-line);stroke-width:1;fill:none}
.o-fig svg .bx{stroke:var(--o-ls);stroke-width:1;fill:none}
.o-fig svg .ln{stroke:var(--o-muted);stroke-width:1.5;fill:none}
.o-fig svg .ln2{stroke:var(--o-muted);stroke-width:1.5;fill:none;stroke-dasharray:5 4}
.o-fig svg .ar{stroke:var(--o-muted);stroke-width:1.2;fill:none}
.o-fig svg .ah,.o-fig svg .dot{fill:var(--o-muted);stroke:none}
.o-fig svg .em{stroke:var(--o-ember);fill:none;stroke-width:1.5}
.o-fig svg .emf{fill:var(--o-ember);stroke:none}
.o-fig figcaption{font-size:14px;color:var(--o-muted);margin-top:10px;line-height:1.7}
.o-fig figcaption .small{font-size:inherit}
/* 伸び: 線は描かれるように現れる（pathLength="1" を付けた線だけ・最初の一度） */
.o-js .o-fig [pathLength]{stroke-dasharray:1;stroke-dashoffset:1}
.o-js .o-fig.o-in [pathLength]{stroke-dashoffset:0;transition:stroke-dashoffset .65s cubic-bezier(.2,.7,.2,1)}
/* rise: 面に来たものが立ち上がる（200ms・4px） */
.o-js .block,.o-js .qblock,.o-js h2,.o-js .o-fig{opacity:0;transform:translateY(4px)}
.o-js .o-in{opacity:1!important;transform:none!important;transition:opacity .2s """ + SETTLE + r""",transform .2s """ + SETTLE + r"""}
@media (max-width:560px){
  body{padding:0 16px 72px}
  h1{font-size:22px}
  h2{font-size:16px}
  .o-row{padding-right:150px}
  .o-toc{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;margin-left:-16px;margin-right:-16px;padding-left:16px;padding-right:16px}
  .o-toc::-webkit-scrollbar{display:none}
  .o-toc a,.o-toc .o-lbl{flex:none}
  .block,.qblock{padding:10px 10px}
  .pt{padding:.4em .7em}
  .tgl{right:16px}
}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .o-js .block,.o-js .qblock,.o-js h2,.o-js .o-fig{opacity:1;transform:none}
  .o-js .o-fig [pathLength]{stroke-dashoffset:0}
}
}
"""

# ---- 問題集アプリ（Pattern 01 のトークン。JS がマークアップを生成する） ----
QUIZ_CSS = r"""
@media screen{
:root:not([data-theme="light"]),:root[data-theme="light"]{
  --paper:var(--o-ground); --panel:transparent; --panel-2:var(--o-glow); --ink:var(--o-paper); --dim:var(--o-faint);
  --line:var(--o-line); --accent:var(--o-ember-text); --accent-contrast:var(--o-ground);
  --good:var(--o-good); --good-bg:var(--o-good-bg); --bad:var(--o-bad); --bad-bg:var(--o-bad-bg);
  --sub:var(--o-muted); --warn-bg:var(--o-glow); --warn-border:var(--o-ember-text);
  --font-jp:""" + SANS + r"""; --font-mono:""" + MONO + r""";
}
body{background-image:radial-gradient(var(--o-dot) 1px,transparent 1.2px)}
.o-head{max-width:1160px;padding:0 20px}
.card,.qCard,.howto,.tableWrap{background:""" + CORNERS + r""";border:1px solid var(--o-line)}
header h1{font-size:16px;font-weight:500;text-transform:none;letter-spacing:.02em}
.badge{background:transparent;color:var(--o-ember-text);border:1px solid var(--o-ember-text);font-family:""" + MONO + r""";font-weight:500}
nav button.examBtn{background:transparent;color:var(--o-ember-text);border-color:var(--o-ember-text)}
nav button.examBtn:hover{background:var(--o-glow)}
.summaryList li::before{background:var(--o-ls)}
.correctAnswer{color:var(--o-paper)}
.progressInner{background:var(--o-ember)}
.themeToggle{min-height:44px;padding:0 12px}
nav button.navBtn,.checkBtn,.bmBtn,.choiceRow,.tabs button{transition:transform .42s """ + SPRING + r""",background-color .15s,border-color .15s,color .15s}
nav button.navBtn:active,.checkBtn:active,.bmBtn:active,.tabs button:active{transform:scale(.94);transition-duration:.07s}
.choiceRow:active{transform:scale(.985);transition-duration:.07s}
}
"""

# ---- 学習帳アプリ（IDENTIFIER v3 のトークン） ----
WORKBOOK_CSS = r"""
@media screen{
:root:not([data-theme="light"]),:root[data-theme="light"]{
  --paper:var(--o-ground); --panel:transparent; --ink:var(--o-paper); --sub:var(--o-muted); --dim:var(--o-faint);
  --line:var(--o-line); --line2:var(--o-dot); --accent:var(--o-ember-text); --accent-ink:var(--o-ground);
  --ok:var(--o-good); --ng:var(--o-bad); --warnc:var(--o-ember-text);
  --mono:""" + MONO + r"""; --sans:""" + SANS + r""";
}
.o-head{max-width:860px;padding:0 clamp(12px,3vw,22px)}
.brand::before{background:var(--o-ember)}
.panel::before,.panel::after,.panel>.bl,.panel>.br{width:5px;height:5px;border:none!important;background:var(--o-ls)}
.panel::before{top:-3px;left:-3px}.panel::after{top:-3px;right:-3px}
.panel>.bl{bottom:-3px;left:-3px}.panel>.br{bottom:-3px;right:-3px}
.panel>h3,section.unit>h2,.f>h3{color:var(--o-faint)}
.tag{color:var(--o-faint);border-color:var(--o-line)}
.fx,.formula{background:transparent;border-left:1px solid var(--o-ls)}
.warn{background:transparent;border-left:2px solid var(--o-ember)}
.note{background:transparent}
.kv th,.data th,.parts th,.vocab th{background:var(--o-glow)}
.sol b{color:var(--o-paper)}
nav#secnav button,.jump a,.presets button,.qtabs button,.mini .grade,#theme-toggle,.flagbtn,.q details>summary{
  transition:transform .42s """ + SPRING + r""",border-color .15s,color .15s}
nav#secnav button:active,.jump a:active,.presets button:active,.qtabs button:active,.mini .grade:active,#theme-toggle:active,.flagbtn:active{
  transform:scale(.94);transition-duration:.07s}
}
"""

# ---- 数式の一覧表（仕様確立前の別構造。変数は色だけ） ----
SHEET_CSS = r"""
@media screen{
:root:not([data-theme="light"]),:root[data-theme="light"]{
  --bg-color:var(--o-ground); --card-bg-color:transparent; --text-color:var(--o-paper); --heading-color:var(--o-paper);
  --accent-color:var(--o-ls); --border-color:var(--o-line); --shadow-color:transparent;
}
body{font-family:""" + SANS + r""";font-size:16px;line-height:1.85;letter-spacing:.02em;
  background-image:radial-gradient(var(--o-dot) 1px,transparent 1.2px);background-size:24px 24px;padding:0 24px 96px}
.container{max-width:980px;padding:0}
header{text-align:left;padding:8px 0 20px;margin-bottom:28px}
header h1{font-size:34px;font-weight:600;letter-spacing:-.02em;line-height:1.3}
.card{position:relative;border-radius:0;box-shadow:none;padding:20px 22px}
.card::before{content:"";position:absolute;inset:-3px;pointer-events:none;background:""" + CORNERS + r"""}
h2{position:relative;font-size:22px;font-weight:500;letter-spacing:-.01em;border-bottom:1px solid var(--o-line);padding:0 0 .35em 17px}
h2::before{content:"";position:absolute;left:0;top:.62em;width:5px;height:5px;background:var(--o-ember)}
h3{font-size:16px;font-weight:500;border-left:1px solid var(--o-ls)}
.katex-display{background:transparent;border-left:1px solid var(--o-ls);border-radius:0}
strong,.highlight{color:var(--o-paper);font-weight:600}
details{border-radius:0}
summary{background:transparent;border-radius:0;font-size:16px;font-weight:500;min-height:44px}
.exam-point{background:transparent;border:1px solid var(--o-line);border-left:2px solid var(--o-ember);border-radius:0}
.exam-point h4{color:var(--o-ember-text);font-size:16px;font-weight:500}
th{background:var(--o-glow);font-weight:500}
td.amount{font-family:""" + MONO + r"""}
.table-caption{color:var(--o-muted);font-size:14px;font-weight:500}
@media (max-width:560px){body{padding:0 16px 72px} header h1{font-size:22px} h2{font-size:16px}}
}
"""

KIND_CSS = {"notes": NOTES_CSS, "quiz": QUIZ_CSS, "workbook": WORKBOOK_CSS, "sheet": SHEET_CSS}
KIND_BY_DEST = C.APP_KINDS

# 既定は鉄紺。明るい表示は本人が選んだとき（studyhub_theme=light）だけ
NOTES_HEAD_JS = (
    "try{var t=localStorage.getItem('studyhub_theme');"
    "document.documentElement.setAttribute('data-theme',t==='light'?'light':'dark');"
    "document.documentElement.classList.add('o-js')}catch(e){document.documentElement.classList.add('o-js')}"
)
# アプリは自前の記憶キーで明暗を決めるため、読み込み前にハブの設定を渡しておく
APP_HEAD_JS = (
    "try{var s=localStorage,t=s.getItem('studyhub_theme')==='light'?'light':'dark';"
    "s.setItem('studyhub_theme',t);" + "".join("s.setItem('%s',t);" % k for k in C.APP_THEME_KEYS)
    + "document.documentElement.setAttribute('data-theme',t)}catch(e){}"
)

NOTES_TAIL_JS = r"""
(function(){
  var D=document.documentElement;
  /* 表示切替の文言を今の表示に合わせる（原本のトグルは system の明暗を既定にしていた） */
  var b=document.getElementById('tgl');
  function paint(){ if(b) b.textContent = D.getAttribute('data-theme')==='light' ? '[LIGHT] ∨ DARK' : 'LIGHT ∨ [DARK]'; }
  if(b){ b.addEventListener('click',function(){ setTimeout(function(){
    try{localStorage.setItem('studyhub_theme',D.getAttribute('data-theme')==='light'?'light':'dark')}catch(e){}
    paint(); },0); }); paint(); }

  /* 回の索引: 「第N回」の見出しが二つ以上あるときだけ出す。今読んでいる回を燠火で示す */
  var hs=[].slice.call(document.querySelectorAll('h2[id]')), toc=document.getElementById('o-toc'), links=[];
  var rounds=hs.filter(function(h){return /第\s*[0-9０-９]+\s*回/.test(h.textContent)});
  if(toc && rounds.length>1){
    var l=document.createElement('span'); l.className='o-lbl'; l.textContent='ROUND'; toc.appendChild(l);
    rounds.forEach(function(h){
      var m=h.textContent.match(/第\s*([0-9０-９]+)\s*回/), n=m[1].replace(/[０-９]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-65248)});
      var a=document.createElement('a'); a.href='#'+h.id; a.textContent=(n.length<2?'0':'')+n; a.title=h.textContent.trim();
      toc.appendChild(a); links.push([h,a]);
    });
  }
  var bar=document.querySelector('.o-progress'), cur=null, ticking=false;
  function frame(){
    ticking=false;
    var max=D.scrollHeight-innerHeight; if(bar) bar.style.transform='scaleX('+(max>0?Math.min(1,scrollY/max):0)+')';
    var now=null; hs.forEach(function(h){ if(h.getBoundingClientRect().top<innerHeight*0.3) now=h; });
    if(now!==cur){
      if(cur) cur.classList.remove('o-now'); if(now) now.classList.add('o-now'); cur=now;
      links.forEach(function(p){
        var on=p[0]===now; p[1].classList.toggle('on',on);
        /* 横に巻ける索引では、今の回を見える位置へ寄せる（縦には動かさない） */
        if(on && toc.scrollWidth>toc.clientWidth){ var a=p[1]; toc.scrollTo({left:a.offsetLeft-toc.clientWidth/2+a.offsetWidth/2,behavior:'smooth'}); }
      });
    }
  }
  addEventListener('scroll',function(){ if(!ticking){ticking=true;requestAnimationFrame(frame)} },{passive:true});
  addEventListener('resize',frame); frame();

  /* rise（最初の一度だけ）。観測が届かなくても画面内の要素は必ず見せる */
  var els=[].slice.call(document.querySelectorAll('.block,.qblock,h2,.o-fig'));
  function show(e){ e.classList.add('o-in'); }
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting){ show(e.target); io.unobserve(e.target); } }); },{rootMargin:'0px 0px -4% 0px'});
    els.forEach(function(e){ io.observe(e); });
  } else els.forEach(show);
  setTimeout(function(){ els.forEach(function(e){ var r=e.getBoundingClientRect(); if(r.top<innerHeight) show(e); }); },1200);
  /* 索引や #リンクで飛んだ先は、観測を待たずに見せる */
  addEventListener('hashchange',function(){ els.forEach(function(e){ if(e.getBoundingClientRect().top<innerHeight) show(e); }); });
})();
"""

# アプリ側の切替ボタンで変えた明暗を、ハブと他の頁へ引き継ぐ
APP_TAIL_JS = r"""
(function(){
  var D=document.documentElement;
  ['themeToggle','theme-toggle'].forEach(function(id){
    var b=document.getElementById(id); if(!b) return;
    b.addEventListener('click',function(){ setTimeout(function(){
      try{localStorage.setItem('studyhub_theme',D.getAttribute('data-theme')==='light'?'light':'dark')}catch(e){}
    },0); });
  });
})();
"""


def head_block(kind):
    js = NOTES_HEAD_JS if kind == "notes" else APP_HEAD_JS
    return ("<!-- " + MARK + ":HEAD v" + VERSION + " -->" + FONTS + "<style>" + BASE_CSS + KIND_CSS[kind]
            + "</style><script>" + js + "</script><!-- /" + MARK + ":HEAD -->")


def tail_block(kind):
    js = NOTES_TAIL_JS if kind == "notes" else APP_TAIL_JS
    return "<!-- " + MARK + ":TAIL -->\n<script>" + js + "</script>\n<!-- /" + MARK + ":TAIL -->"


def body_block(code, title, kind):
    notes = kind == "notes"
    return ("<!-- " + MARK + ":BODY -->"
            + ("<div class=\"o-progress\" aria-hidden=\"true\"></div>" if notes else "")
            + "<div class=\"o-head\"><div class=\"o-band\"></div><div class=\"o-row\">"
            "<a class=\"o-back\" href=\"../\"><span class=\"o-arrow\"></span>STUDY HUB</a>"
            "<span class=\"o-beacon\"></span><span class=\"o-face\">" + esc(code) + "<i>∧</i>" + esc(title) + "</span>"
            "</div></div>"
            + ("<nav class=\"o-toc\" id=\"o-toc\" aria-label=\"回の索引\"></nav>" if notes else "")
            + "<!-- /" + MARK + ":BODY -->")


BLOCK_RE = re.compile(r"\r?\n?<!-- " + MARK + r":(HEAD|BODY|TAIL)[^>]*-->.*?<!-- /" + MARK + r":\1 -->", re.S)


def strip(text):
    return BLOCK_RE.sub("", text)


def skin(text, code, title, kind="notes"):
    """原本の文字列に層を入れた文字列を返す。改行コードは原本に合わせる。"""
    nl = "\r\n" if "\r\n" in text else "\n"
    t = strip(text)
    i = t.lower().rfind("</head>")
    j = re.search(r"<body[^>]*>", t, re.I)
    k = t.lower().rfind("</body>")
    if i < 0 or not j or k < 0:
        raise ValueError("head/body が見つからない")
    t = t[:k] + tail_block(kind).replace("\n", nl) + nl + t[k:]
    t = t[:j.end()] + nl + body_block(code, title, kind) + t[j.end():]
    i = t.lower().rfind("</head>")
    t = t[:i] + head_block(kind) + nl + t[i:]
    return t


def kind_of(item, text):
    if "--ctx-bar" in text:
        return "notes"
    return KIND_BY_DEST.get(item["dest"].split("/", 1)[0])


def targets():
    spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)
    for it in b.MANIFEST:
        if "src" not in it:
            continue
        path = it["src"] if os.path.isabs(it["src"]) else os.path.join(b.SRC_BASE, it["src"])
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
        kind = kind_of(it, strip(text))
        if kind:
            yield it, path, text, kind


def main():
    check = "--check" in sys.argv
    changed, stale = 0, []
    for it, path, text, kind in targets():
        new = skin(text, it["code"], it["title"], kind)
        if new == text:
            continue
        if check:
            stale.append(it["course"])
            continue
        # Mac の既定の改行変換は `\n` を変えないため、原本の CRLF はそのまま残る（atomicio の注記を参照）
        atomicio.write_text(path, new)
        changed += 1
    if check:
        print("未適用・古い層: %d 頁%s" % (len(stale), (" (" + "、".join(stale) + ")") if stale else ""))
        sys.exit(1 if stale else 0)
    print("適用: %d 頁を更新" % changed)


if __name__ == "__main__":
    main()
