# -*- coding: utf-8 -*-
"""専門演習（ゼミ）比較ダッシュボード public/zemi/ を組む。

正本は zemi.json（zemi_extract.py ＋ 画像頁の書き起こし）。説明文は原文のまま載せる（改行の整形と互換文字の正規化のみ）。
分野（データサイエンス／ビジネス・データサイエンス／ビジネス）・本文からの自動検出タグ・全文検索で絞り込み、
最大4人を並べて比較し、希望順（第1〜15）を端末内に保存できる。個別説明会一覧表は頁を画像で載せる。

    python -X utf8 zemi_build.py
"""
import glob
import json
import os
import re
import shutil

import fitz

import atomicio
from hub_style import FONTS, CSS as HUB_CSS, esc

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "zemi.json")
OUT = os.path.join(ROOT, "public", "zemi")
SRC_DIR = None   # 一覧表PDFの場所（site_config.SRC_BASE/2026_秋/専門演習/資料）

ZCSS = r"""
.wrap{max-width:1180px}
.zh{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:6px 0 4px}
.zh a.back{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--faint);text-decoration:none}
.zh h1{font-size:22px;font-weight:500;margin:0}
.zh .lbl{font-family:var(--mono);font-size:11px;letter-spacing:.14em;color:var(--faint)}
.dates{display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 14px;font-size:13px;color:var(--muted)}
.dates b{font-family:var(--mono);font-weight:500;color:var(--ink)}
.dates .hot b{color:var(--ember-text)}
.tabs{display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:8px 0 12px}
.tabs button{font:inherit;font-size:14px;background:none;border:1px solid transparent;border-bottom:none;color:var(--faint);padding:8px 14px;cursor:pointer;min-height:40px}
.tabs button.on{border-color:var(--line);color:var(--ink);background:var(--glow)}
.ctl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.chip{font:inherit;font-size:13px;border:1px solid var(--line);background:none;color:var(--muted);padding:6px 12px;cursor:pointer;min-height:36px}
.chip.on{border-color:var(--line-strong);color:var(--ink);background:var(--glow)}
.chip .n{font-family:var(--mono);font-size:11px;color:var(--faint);margin-left:6px}
.chip.f-ds.on{box-shadow:inset 3px 0 0 #6FA3C8}.chip.f-bds.on{box-shadow:inset 3px 0 0 #9DB7A1}.chip.f-b.on{box-shadow:inset 3px 0 0 #C9A66B}
.q{flex:1 1 260px;font:inherit;font-size:15px;background:none;border:1px solid var(--line);color:var(--ink);padding:8px 12px;min-height:40px}
.sel{font:inherit;font-size:13px;background:var(--ground);color:var(--ink);border:1px solid var(--line);padding:6px 8px;min-height:36px}
.tagrow{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 10px}
.tag{font-size:12px;border:1px solid var(--line);color:var(--muted);padding:3px 8px;cursor:pointer;background:none;font-family:inherit}
.tag.on{border-color:var(--ember);color:var(--ink)}
.hint{font-size:12.5px;color:var(--faint);margin:2px 0 10px}
.count{font-family:var(--mono);font-size:12px;color:var(--faint);margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.card{border:1px solid var(--line);padding:14px 16px 12px;position:relative;display:flex;flex-direction:column;gap:6px}
.card .top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.card .nm{font-size:17px;font-weight:500}
.card .rd{font-size:12px;color:var(--faint)}
.fld{font-size:11.5px;padding:2px 7px;border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.fld.ds{border-color:#6FA3C8}.fld.bds{border-color:#9DB7A1}.fld.b{border-color:#C9A66B}
.card .th{font-size:15px;line-height:1.6;white-space:pre-wrap}
.card .tg{display:flex;flex-wrap:wrap;gap:4px}
.card .tg span{font-size:11px;color:var(--faint);border:1px dashed var(--line);padding:1px 6px}
.card .act{display:flex;gap:6px;margin-top:4px;flex-wrap:wrap}
.btn{font:inherit;font-size:13px;background:none;border:1px solid var(--line);color:var(--muted);padding:6px 10px;cursor:pointer;min-height:36px}
.btn.on{border-color:var(--ember);color:var(--ink)}
.btn:hover{border-color:var(--line-strong)}
.full{border-top:1px dashed var(--line);margin-top:6px;padding-top:6px}
.sec{margin:8px 0}
.sec h4{font-size:12px;font-weight:500;color:var(--faint);letter-spacing:.06em;margin:0 0 3px}
.sec p{margin:0;font-size:14.5px;line-height:1.85;white-space:pre-wrap}
mark{background:rgba(228,87,46,.28);color:inherit}
.cmpbar{position:sticky;bottom:0;background:var(--ground);border-top:1px solid var(--line-strong);padding:8px 0;display:flex;gap:8px;align-items:center;flex-wrap:wrap;z-index:5}
.cmp{overflow-x:auto}
.cmp table{border-collapse:collapse;min-width:100%}
.cmp th,.cmp td{border:1px solid var(--line);vertical-align:top;padding:10px 12px;text-align:left}
.cmp th{font-size:12px;font-weight:500;color:var(--faint);white-space:nowrap;position:sticky;left:0;background:var(--ground)}
.cmp td{min-width:260px;max-width:420px;font-size:14px;line-height:1.8;white-space:pre-wrap}
.cmp td.h{font-size:15px;font-weight:500;white-space:normal}
.wish ol{padding-left:0;list-style:none;margin:0}
.wish li{display:grid;grid-template-columns:5.2em 1fr auto;gap:10px;align-items:center;border-top:1px solid var(--line);padding:8px 0}
.wish li .k{font-family:var(--mono);font-size:12px;color:var(--faint)}
.wish li.req .k{color:var(--ember-text)}
.front p{white-space:pre-wrap;font-size:14.5px;line-height:1.85}
.sched img{max-width:100%;border:1px solid var(--line);background:#fff;margin:8px 0}
.empty{color:var(--faint);font-size:14px;padding:12px 0}
.kw{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0 2px}
.kwb{font:inherit;font-size:12px;line-height:1.4;padding:2px 8px;min-height:26px;border:1px solid var(--line);background:none;color:var(--muted);cursor:pointer}
.kwb:hover{border-color:var(--line-strong);color:var(--ink)}
.info dl{display:grid;grid-template-columns:6.5em 1fr;gap:4px 10px;margin:4px 0;font-size:13.5px;line-height:1.7}
.info dt{color:var(--faint)}.info dd{margin:0}.info ul{margin:0;padding-left:1.1em}
.info a.src{font-family:var(--mono);font-size:11px;color:var(--faint);margin-left:4px;white-space:nowrap}
.info a{color:var(--ink);word-break:break-all}
@media (max-width:560px){.info dl{grid-template-columns:1fr}.info dt{margin-top:4px}}
.ses{border-top:1px dashed var(--line);margin-top:6px;padding-top:6px;font-size:13.5px;line-height:1.7}
.ses h4{font-size:12px;font-weight:500;color:var(--faint);margin:0 0 2px}
.ses .r{display:grid;grid-template-columns:7.2em 1fr;gap:2px 8px}
.ses .r.past{opacity:.45}
.ses .r.next b{color:var(--ember-text)}
.ses .d{font-family:var(--mono);font-size:12.5px}
.ses .more{font-size:12.5px;color:var(--faint)}
.ses a,.day a{color:var(--ink)}
.dayctl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:8px 0}
.dayctl label{font-size:13px;color:var(--muted);display:flex;gap:6px;align-items:center;min-height:36px}
.day{margin:14px 0}
.day h3{font-family:var(--mono);font-size:14px;font-weight:500;margin:0 0 4px;padding-bottom:4px;border-bottom:1px solid var(--line-strong)}
.day h3 .warn{font-family:var(--sans);font-size:12px;color:var(--ember-text);margin-left:10px}
.day .row{display:grid;grid-template-columns:8.6em 1fr auto;gap:4px 12px;padding:6px 0;border-bottom:1px solid var(--line);align-items:baseline}
.day .row .tm{font-family:var(--mono);font-size:13px}
.day .row .tm small{display:block;font-family:var(--sans);font-size:11.5px;color:var(--faint)}
.day .row .pl{font-family:var(--mono);font-size:13px;color:var(--muted);text-align:right}
.day.past{opacity:.5}
.notes{font-size:13px;color:var(--muted);line-height:1.8;margin:6px 0 10px}
@media (max-width:560px){.day .row{grid-template-columns:6.6em 1fr}.day .row .pl{grid-column:2;text-align:left}}
.src{font-size:12.5px;color:var(--faint);margin-top:18px;line-height:1.8}
@media (max-width:560px){.grid{grid-template-columns:1fr}.cmp td{min-width:220px}}
"""

APP = r"""
(function(){
var D=JSON.parse(document.getElementById('zemi-data').textContent);
var T=D.teachers, WK='zemi_wish_v1', CK='zemi_cmp_v1';
function get(k){try{return JSON.parse(localStorage.getItem(k)||'null')}catch(e){return null}}
function put(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
var wish=get(WK)||[], cmp=get(CK)||[];
var FK={'データサイエンス':'ds','ビジネス・データサイエンス':'bds','ビジネス':'b'};
var fields={'データサイエンス':1,'ビジネス・データサイエンス':1,'ビジネス':1};
var tagsOn={}, q='', sort='page', tab='list', open={};
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function hl(s){s=esc(s);if(!q)return s;var ws=q.split(/\s+/).filter(Boolean);ws.forEach(function(w){var re=new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');s=s.replace(re,function(m){return '<mark>'+m+'</mark>'})});return s}
function full(t){return [t.name,t.reading||'',t.theme_index,t.field].concat(t.sections.map(function(s){return s.title+' '+s.text})).join(' ')}
T.forEach(function(t){t._full=full(t);t._tags=D.tagrules.filter(function(r){return new RegExp(r[1]).test(t._full)}).map(function(r){return r[0]})});
function visible(){
  var ws=q.split(/\s+/).filter(Boolean);
  var on=Object.keys(tagsOn).filter(function(k){return tagsOn[k]});
  var L=T.filter(function(t){
    if(!fields[t.field])return false;
    if(on.some(function(k){return t._tags.indexOf(k)<0}))return false;
    return ws.every(function(w){return t._full.toLowerCase().indexOf(w.toLowerCase())>=0});
  });
  L.sort(function(a,b){
    if(sort==='wish'){var ia=wish.indexOf(a.page),ib=wish.indexOf(b.page);ia=ia<0?99:ia;ib=ib<0?99:ib;if(ia!==ib)return ia-ib}
    if(sort==='field'&&a.field!==b.field)return a.field<b.field?-1:1;
    if(sort==='name')return a.name<b.name?-1:1;
    return a.page-b.page});
  return L;
}
function secHTML(t){return t.sections.map(function(s){return '<div class="sec"><h4>'+esc((s.no?s.no+'．':'')+s.title)+'</h4><p>'+hl(s.text)+'</p></div>'}).join('')+(t.note?'<p class="hint">'+esc(t.note)+'</p>':'')}
var TODAY=(function(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)})();
function md(ds){var a=ds.split('-');return (+a[1])+'/'+(+a[2])}
function tm(x){return x.start?(x.start+(x.label==='昼休み'&&x.mode==='対面'?'頃':'')+(x.end?'–'+x.end:'〜')):''}
function sesLine(x){return '<span class="d">'+md(x.date)+'（'+x.dow+'）</span><span><b>'+tm(x)+'</b>'+(x.label?' '+esc(x.label):'')
  +(x.mode==='対面'?' ＠'+esc(x.place||''):' リアルタイム配信'+(x.url?' <a href="'+esc(x.url)+'" target="_blank" rel="noopener">接続</a>':'')+(x.place?'（学内視聴は'+esc(x.place)+'）':''))+'</span>'}
function sesHTML(t){
  var S=(D.sessions||[]).filter(function(x){return x.p===t.page}), up=S.filter(function(x){return x.date>=TODAY}), past=S.length-up.length;
  var h='<div class="ses"><h4>個別説明会</h4>';
  if(!S.length&&!D.ondemand[t.page]) h+='<div class="more">対面・リアルタイム配信の予定なし</div>';
  var show=open[t.page]?S:up.slice(0,4);
  show.forEach(function(x,i){h+='<div class="r'+(x.date<TODAY?' past':'')+(x===up[0]?' next':'')+'">'+sesLine(x)+'</div>'});
  if(!open[t.page]&&up.length>4) h+='<div class="more">ほか '+(up.length-4)+' 回（「全文」で全部表示）</div>';
  if(!open[t.page]&&past) h+='<div class="more">終わった回 '+past+' 回</div>';
  if(D.ondemand[t.page]) h+='<div class="r"><span class="d">配信</span><span>オンデマンド配信 '+esc(D.ondemand[t.page])+(D.lms?'（資料は'+esc(D.lms)+'）':'')+'</span></div>';
  if(open[t.page]&&D.realtime&&D.realtime[t.page]) h+='<div class="r"><span class="d">注記</span><span>'+esc(D.realtime[t.page]).replace(/\n/g,'<br>')+'</span></div>';
  if(D.other[t.page]) h+='<div class="r"><span class="d">その他</span><span>'+esc(D.other[t.page])+'</span></div>';
  return h+'</div>';
}
function kwHTML(t){var k=(D.info.keywords||{})[t.page]||[];return k.length?'<div class="kw">'+k.map(function(x){return '<button class="kwb" data-a="kw" data-k="'+esc(x)+'">'+esc(x)+'</button>'}).join('')+'</div>':''}
function srcA(o){if(!o||!o.src)return '';var h=o.src.replace(/^https?:\/\//,'').split('/')[0];return ' <a class="src" href="'+esc(o.src)+'" target="_blank" rel="noopener">'+esc(h)+'</a>'}
function infoHTML(t){
  var p=(D.info.profiles||{})[t.page]; if(!p) return '';
  var r=[];
  function row(k,v){if(v)r.push('<dt>'+k+'</dt><dd>'+v+'</dd>')}
  if(p.position) row('職位',esc(p.position.value)+srcA(p.position));
  if(p.fields&&p.fields.value&&p.fields.value.length) row('専門',esc(p.fields.value.join('・'))+srcA(p.fields));
  if(p.degree) row('学位',esc(p.degree.value)+srcA(p.degree));
  function lst(L){var one=L.every(function(c){return c.src===L[0].src});return '<ul>'+L.map(function(c){return '<li>'+esc(c.value)+(one?'':srcA(c))+'</li>'}).join('')+'</ul>'+(one?'<div>出典'+srcA(L[0])+'</div>':'')}
  if(p.career&&p.career.length) row('経歴',lst(p.career));
  if(p.lab_url) row('研究室','<a href="'+esc(p.lab_url.value)+'" target="_blank" rel="noopener">'+esc(p.lab_url.value)+'</a>');
  if(p.notes&&p.notes.length) row('補足',lst(p.notes));
  if(p.material_links&&p.material_links.length) row('資料中のリンク','<ul>'+p.material_links.map(function(m){return '<li><a href="'+esc(m.url)+'" target="_blank" rel="noopener">'+esc(m.url)+'</a><br>'+esc(m.summary||(m.ok?'':'（開けなかった）'))+'</li>'}).join('')+'</ul>');
  if(!r.length) return '<div class="sec info"><h4>資料と公開情報</h4><p class="hint">大学の教員紹介・researchmap・KAKEN では、この担任者の情報を確かめられなかった（'+esc(p.accessed||'')+' 時点）。</p></div>';
  return '<div class="sec info"><h4>資料と公開情報</h4><dl>'+r.join('')+'</dl><p class="hint">大学・researchmap・研究室など公式の公開情報から、'+esc(p.accessed||'')+' に取得した職業上の情報のみ。右の灰色の語は出典。最新の情報は出典で確かめること。</p></div>';
}
function card(t){
  var w=wish.indexOf(t.page), c=cmp.indexOf(t.page)>=0;
  return '<article class="card" id="z'+t.page+'"><div class="top"><span class="nm">'+hl(t.name)+'</span>'+(t.reading?'<span class="rd">'+esc(t.reading)+'</span>':'')
   +'<span class="fld '+FK[t.field]+'">'+esc(t.field)+'</span><span class="rd">p.'+t.page+'</span></div>'
   +'<div class="th">'+hl(t.theme)+'</div>'
   +'<div class="tg">'+t._tags.map(function(x){return '<span>'+esc(x)+'</span>'}).join('')+'</div>'
   +kwHTML(t)
   +'<div class="act"><button class="btn" data-a="open" data-p="'+t.page+'">'+(open[t.page]?'閉じる':'全文')+'</button>'
   +'<button class="btn'+(c?' on':'')+'" data-a="cmp" data-p="'+t.page+'">'+(c?'比較から外す':'比べる')+'</button>'
   +'<button class="btn'+(w>=0?' on':'')+'" data-a="wish" data-p="'+t.page+'">'+(w>=0?'第'+(w+1)+'希望 ✓':'希望に入れる')+'</button></div>'
   +sesHTML(t)+(open[t.page]?'<div class="full">'+secHTML(t)+infoHTML(t)+'</div>':'')+'</article>';
}
function byPage(p){return T.filter(function(t){return t.page===p})[0]}
function renderList(){
  var L=visible();
  document.getElementById('cnt').textContent=L.length+' / '+T.length+' 名';
  document.getElementById('grid').innerHTML=L.map(card).join('')||'<div class="empty">条件に合うゼミはない。</div>';
}
function renderCmp(){
  var P=cmp.map(byPage).filter(Boolean), el=document.getElementById('cmpview');
  if(!P.length){el.innerHTML='<div class="empty">一覧で「比べる」を押すと、最大4人まで並べて比較できる。</div>';return}
  var titles=[];P.forEach(function(t){t.sections.forEach(function(s){if(titles.indexOf(s.title)<0)titles.push(s.title)})});
  var h='<table><tr><th>担任者</th>'+P.map(function(t){return '<td class="h">'+esc(t.name)+'<br><span class="fld '+FK[t.field]+'">'+esc(t.field)+'</span> <button class="btn" data-a="cmp" data-p="'+t.page+'">外す</button></td>'}).join('')+'</tr>';
  h+='<tr><th>自動検出タグ</th>'+P.map(function(t){return '<td>'+esc(t._tags.join('、')||'—')+'</td>'}).join('')+'</tr>';
  titles.forEach(function(ti){h+='<tr><th>'+esc(ti)+'</th>'+P.map(function(t){var s=t.sections.filter(function(x){return x.title===ti})[0];return '<td>'+(s?hl(s.text):'—')+'</td>'}).join('')+'</tr>'});
  el.innerHTML=h+'</table>';
}
function renderWish(){
  var el=document.getElementById('wishview');
  if(!wish.length){el.innerHTML='<div class="empty">一覧で「希望に入れる」を押すと、ここで順番を並べ替えられる（第1〜5希望は申込で必須、第6〜15は任意）。記録はこの端末の中だけに残る。</div>';return}
  el.innerHTML='<ol>'+wish.map(function(p,i){var t=byPage(p);if(!t)return '';return '<li class="'+(i<5?'req':'')+'"><span class="k">第'+(i+1)+'希望</span><span><a href="#z'+p+'" data-a="goto" data-p="'+p+'">'+esc(t.name)+'</a>　<span class="fld '+FK[t.field]+'">'+esc(t.field)+'</span><br><span class="hint">'+esc(t.theme)+'</span></span>'
   +'<span><button class="btn" data-a="up" data-p="'+p+'">↑</button> <button class="btn" data-a="down" data-p="'+p+'">↓</button> <button class="btn" data-a="wish" data-p="'+p+'">外す</button></span></li>'}).join('')+'</ol>'
   +'<p><button class="btn" data-a="copy">希望順を文字でコピー</button> <span class="hint" id="copied"></span></p>'+(wish.length<5?'<p class="hint">第5希望まではすべて必須。あと'+(5-wish.length)+'つ選ぶ。</p>':'');
}
var onlyWish=false, showPast=false;
function renderSched(){
  var S=(D.sessions||[]).filter(function(x){var t=byPage(x.p);return t&&fields[t.field]&&(!onlyWish||wish.indexOf(x.p)>=0)&&(showPast||x.date>=TODAY)});
  var days={},order=[];S.forEach(function(x){if(!days[x.date]){days[x.date]=[];order.push(x.date)}days[x.date].push(x)});
  var h='';
  order.forEach(function(ds){var L=days[ds];h+='<section class="day'+(ds<TODAY?' past':'')+'"><h3>'+md(ds)+'（'+L[0].dow+'）'+(ds===TODAY?' 今日':'')
    +(D.dayNotes[ds]?'<span class="warn">'+esc(D.dayNotes[ds])+'</span>':'')+'</h3>';
    L.forEach(function(x){var t=byPage(x.p);h+='<div class="row"><span class="tm">'+tm(x)+(x.label?'<small>'+esc(x.label)+'</small>':'')+'</span>'
      +'<span><a href="#z'+x.p+'" data-a="goto" data-p="'+x.p+'">'+esc(t.name)+'</a> <span class="fld '+FK[t.field]+'">'+esc(t.field)+'</span>'+(wish.indexOf(x.p)>=0?' <span class="rd">第'+(wish.indexOf(x.p)+1)+'希望</span>':'')+'</span>'
      +'<span class="pl">'+(x.mode==='対面'?'＠'+esc(x.place||''):'配信'+(x.url?' <a href="'+esc(x.url)+'" target="_blank" rel="noopener">接続</a>':'')+(x.place?'<br><small>学内視聴 '+esc(x.place)+'</small>':''))+'</span></div>'});
    h+='</section>'});
  document.getElementById('dayview').innerHTML=h||'<div class="empty">条件に合う回はない。</div>';
}
function renderBar(){
  document.getElementById('cmpn').textContent=cmp.length;
  document.getElementById('wishn').textContent=wish.length;
}
function render(){
  ['list','cmp','wish','sched','front'].forEach(function(k){document.getElementById('v-'+k).style.display=(tab===k?'':'none');document.getElementById('t-'+k).className=(tab===k?'on':'')});
  if(tab==='list')renderList(); if(tab==='cmp')renderCmp(); if(tab==='wish')renderWish(); if(tab==='sched')renderSched(); renderBar();
}
document.addEventListener('click',function(e){
  var b=e.target.closest('[data-a]'); if(!b)return; var a=b.getAttribute('data-a'), p=+b.getAttribute('data-p');
  if(a==='open'){open[p]=!open[p]}
  else if(a==='cmp'){var i=cmp.indexOf(p);if(i>=0)cmp.splice(i,1);else{if(cmp.length>=4){alert('比較は4人まで。どれかを外してから追加する。');return}cmp.push(p)}put(CK,cmp)}
  else if(a==='wish'){var j=wish.indexOf(p);if(j>=0)wish.splice(j,1);else{if(wish.length>=15){alert('希望は第15希望まで。');return}wish.push(p)}put(WK,wish)}
  else if(a==='up'||a==='down'){var k=wish.indexOf(p),n=a==='up'?k-1:k+1;if(n<0||n>=wish.length)return;wish[k]=wish[n];wish[n]=p;put(WK,wish)}
  else if(a==='goto'){e.preventDefault();tab='list';open[p]=true;render();var el=document.getElementById('z'+p);if(el)el.scrollIntoView({block:'start'});return}
  else if(a==='copy'){var txt=wish.map(function(p,i){var t=byPage(p);return '第'+(i+1)+'希望：'+t.name+'（'+t.field+'）'}).join('\n');try{navigator.clipboard.writeText(txt);document.getElementById('copied').textContent='コピーした'}catch(x){}return}
  else if(a==='kw'){q=b.getAttribute('data-k');document.getElementById('q').value=q;tab='list'}
  else if(a==='tab'){tab=b.getAttribute('data-t')}
  else if(a==='field'){var f=b.getAttribute('data-f');fields[f]=!fields[f];b.classList.toggle('on',fields[f])}
  else if(a==='preset'){var v=b.getAttribute('data-v');Object.keys(fields).forEach(function(k){fields[k]=v==='all'||(v==='data'&&k!=='ビジネス')||(v==='biz'&&k!=='データサイエンス')});document.querySelectorAll('[data-a=field]').forEach(function(c){c.classList.toggle('on',!!fields[c.getAttribute('data-f')])})}
  else if(a==='tag'){var g=b.getAttribute('data-g');tagsOn[g]=!tagsOn[g];b.classList.toggle('on',!!tagsOn[g])}
  else return;
  render();
});
document.getElementById('q').addEventListener('input',function(e){q=e.target.value.trim();renderList()});
document.getElementById('sort').addEventListener('change',function(e){sort=e.target.value;renderList()});
document.getElementById('ow').addEventListener('change',function(e){onlyWish=e.target.checked;renderSched()});
document.getElementById('sp').addEventListener('change',function(e){showPast=e.target.checked;renderSched()});
/* ハブのダッシュボードから #sched（日程）・#z頁（そのゼミ）で直接開く */
var hm=location.hash.match(/^#(sched|z(\d+))$/);
if(hm){if(hm[2]){open[+hm[2]]=true}else{tab='sched'}}
render();
if(hm&&hm[2]){try{history.scrollRestoration='manual'}catch(e){}window.addEventListener('load',function(){setTimeout(function(){var ze=document.getElementById('z'+hm[2]);if(ze)ze.scrollIntoView({block:'start'})},0)})}
})();
"""


def tagrules():
    """本文からの自動検出タグ（表示の補助。本文は変えない）。"""
    return [
        ["PBL演習の指定", "PBL"],
        ["授業時間外の活動", "授業時間外|時間割上の授業時間によらず|授業期間外|夏休み|春休み|長期休暇"],
        ["ゼミ合宿", "合宿"],
        ["自己負担の費用", "自己負担|費用|サブスク"],
        ["卒業論文", "卒業論文|卒論"],
        ["学会・学外発表", "学会|学外発表|対外発表|コンペ|コンテスト|大会"],
        ["企業・実データ", "企業の実データ|実データ|企業から|企業や外部|企業と|産学"],
        ["生成AI・LLM", "生成AI|LLM|ChatGPT|Gemini"],
        ["プログラミング", "プログラミング|Python|python|コード"],
        ["統計・数学", "統計|数学"],
        ["機械学習・深層学習", "機械学習|深層学習|ディープラーニング"],
        ["マーケティング・消費者", "マーケティング|消費者|購買|小売"],
        ["経営・組織", "経営|組織|マネジメント|イノベーション"],
        ["IoT・センサ・計算基盤", "IoT|センサ|分散|クラウド|高性能計算|ネットワーク"],
        ["輪講・文献", "輪講|文献|論文を読"],
        ["選考・面接・課題", "面接|選考|課題を提出|事前課題|レポートを提出"],
        ["大学院進学", "大学院"],
        ["Slack", "Slack"],
    ]


def schedule_data(sc):
    """一覧表の取り込み結果を、表示用の回（session）の列に直す。1つのセルに複数の時限があれば別の回にする。"""
    import datetime
    if not sc:
        return {"sessions": [], "ondemand": {}, "other": {}, "schedNotes": [], "lms": None, "dayNotes": {}}
    W = "月火水木金土日"
    dow = lambda ds: W[datetime.date.fromisoformat(ds).weekday()]
    ses = []
    for x in sc["inperson"]:
        for sl in x["slots"]:
            ses.append({"p": x["page"], "date": x["date"], "dow": x["dow"] or dow(x["date"]), "start": sl["start"],
                        "end": sl["end"], "label": sl["label"], "place": x["place"], "mode": "対面", "raw": x["raw"]})
    for x in sc["online"]:
        for sl in x.get("sessions", []):
            ses.append({"p": x["page"], "date": sl["date"], "dow": dow(sl["date"]), "start": sl["start"], "end": sl["end"],
                        "label": "", "place": sl.get("room"), "mode": "リアルタイム配信", "url": sl["url"], "raw": x["realtime"]})
    ses.sort(key=lambda z: (z["date"], (z["start"] or "99:99").zfill(5), z["p"] or 0))
    ond = {str(x["page"]): x["ondemand"] for x in sc["online"] if x["ondemand"] and x["ondemand"] != "なし" and x["page"]}
    rt = {str(x["page"]): x["realtime"] for x in sc["online"] if x["realtime"].strip() not in ("", "なし") and x["page"]}
    oth = {str(x["page"]): x["text"] for x in sc["other"] if x["page"]}
    notes = []
    for n in sc["notes"]:
        if n["page"] not in (1, 4):
            continue
        for x in n["lines"]:   # 「・」で始まらない行は、前の「・」の行の折り返し
            if notes and notes[-1].startswith("・") and not x.startswith(("・", "〔", "●", "（", "(")) and n["page"] == 4:
                notes[-1] += x
            else:
                notes.append(x)
    lms = next((m.group(1) for x in notes for m in [re.search(r"資料は、?(.+?)に掲載", x)] if m), None)
    dayn = {k: "".join(v) for k, v in sc.get("daynotes", {}).items()}
    return {"sessions": ses, "ondemand": ond, "realtime": rt, "other": oth, "schedNotes": notes, "lms": lms, "dayNotes": dayn}


def sched_images(pdf, out_dir):
    names = []
    if not pdf or not os.path.isfile(pdf):
        return names
    d = fitz.open(pdf)
    for i, pg in enumerate(d):
        fn = "sched_p%d.png" % (i + 1)
        pg.get_pixmap(dpi=110).save(os.path.join(out_dir, fn))
        names.append(fn)
    return names


def build():
    import site_config as C
    if not os.path.isfile(DATA):
        print("zemi: zemi.json がないので作らない")
        return
    d = json.load(open(DATA, encoding="utf-8"))
    src_dir = os.path.join(C.SRC_BASE, "2026_秋", "専門演習", "資料")
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    imgs = sched_images(os.path.join(src_dir, "専門演習_個別説明会一覧表.pdf"), OUT)
    teachers = []
    for t in d["teachers"]:
        if not t.get("sections"):
            secs = [{"no": "", "title": "（未書き起こし）", "text": "この頁は画像のみで、まだ書き起こしていない。履修要項PDFの p.%d を参照。" % t["page"]}]
        else:
            secs = t["sections"]
        th = next((s["text"] for s in secs if s["title"] == "テーマ"), t["theme_index"])
        teachers.append({"page": t["page"], "name": t["name"].replace(" ※", "").strip(), "star": "※" in t["name"],
                         "reading": t.get("reading"), "field": t["field"], "theme_index": t["theme_index"],
                         "theme": th, "sections": secs, "note": t.get("note")})
    data = {"teachers": teachers, "tagrules": tagrules(), "front": d.get("front", {})}
    ip = os.path.join(ROOT, "zemi_info.json")   # キーワードと公開情報（git 管理外。ZEMI_PLAN 第4段）
    data["info"] = json.load(open(ip, encoding="utf-8")) if os.path.isfile(ip) else {"keywords": {}, "profiles": {}}
    data.update(schedule_data(d.get("schedule")))
    counts = {f: sum(1 for t in teachers if t["field"] == f) for f in ("データサイエンス", "ビジネス・データサイエンス", "ビジネス")}
    front = "".join('<section class="front"><h3>履修要項 p.%s</h3><p>%s</p></section>' % (esc(k), esc(v))
                    for k, v in sorted(d.get("front", {}).items(), key=lambda x: int(x[0])))
    js_data = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = (
        '<div class="zh"><a class="back" href="../">← STUDY HUB</a><span class="lbl">SEMINAR ∧ 2027</span><h1>専門演習（ゼミ）を比べる</h1></div>'
        '<div class="dates"><span>個別説明会 <b>10/20〜11/9</b></span><span class="hot">事前確認（お試し）フォーム <b>10/31 17:00</b>まで</span>'
        '<span class="hot">申込 <b>11/10 9:00〜11/12 17:00</b>（17時締切）</span><span>結果発表 <b>12/22</b></span>'
        '<span>希望：第1〜5は必須・第6〜15は任意</span></div>'
        '<p class="hint">学部の1期生のため、どのゼミも2027年度が初めての開講である（先輩・卒業生はいない）。雰囲気や時間外の負担は説明会で直接確かめる。</p>'
        '<nav class="tabs">'
        '<button id="t-list" data-a="tab" data-t="list">一覧</button>'
        '<button id="t-cmp" data-a="tab" data-t="cmp">並べて比較（<span id="cmpn">0</span>）</button>'
        '<button id="t-wish" data-a="tab" data-t="wish">希望リスト（<span id="wishn">0</span>）</button>'
        '<button id="t-sched" data-a="tab" data-t="sched">個別説明会の日程</button>'
        '<button id="t-front" data-a="tab" data-t="front">履修要項の前書き</button></nav>'
        '<div id="v-list">'
        '<div class="ctl">'
        + "".join('<button class="chip f-%s on" data-a="field" data-f="%s">%s<span class="n">%d</span></button>'
                  % (k, esc(f), esc(f), counts[f]) for f, k in (("データサイエンス", "ds"), ("ビジネス・データサイエンス", "bds"), ("ビジネス", "b")))
        + '<button class="chip" data-a="preset" data-v="data">データ寄り（DS＋B・DS）</button>'
        '<button class="chip" data-a="preset" data-v="biz">ビジネス寄り（B＋B・DS）</button>'
        '<button class="chip" data-a="preset" data-v="all">すべて</button></div>'
        '<div class="ctl"><input class="q" id="q" type="search" placeholder="語句で絞り込む（空白で区切ると全部を含むもの）" aria-label="全文検索">'
        '<select class="sel" id="sort" aria-label="並べ順"><option value="page">履修要項の順</option><option value="field">分野ごと</option>'
        '<option value="name">氏名順</option><option value="wish">希望順を先に</option></select><span class="count" id="cnt"></span></div>'
        '<div class="tagrow">' + "".join('<button class="tag" data-a="tag" data-g="%s">%s</button>' % (esc(r[0]), esc(r[0])) for r in tagrules()) + '</div>'
        '<p class="hint">タグは本文の語から自動で付けた目安（例：「PBL」を含む → PBL演習の指定）。条件は本文で確かめること。複数選ぶと全部を満たすゼミだけが残る。</p>'
        '<div class="grid" id="grid"></div></div>'
        '<div id="v-cmp" class="cmp"><div id="cmpview"></div></div>'
        '<div id="v-wish" class="wish"><div id="wishview"></div></div>'
        '<div id="v-sched" class="sched"><span id="sched"></span>'
        '<div class="notes">' + "<br>".join(esc(x) for x in data.get("schedNotes", []) if x.startswith("・")) + '</div>'
        '<p class="hint">時限は大学の標準時程で時刻に直した（1限9:00・2限10:40・3限13:00・4限14:40・5限16:20、各90分。昼休みは一覧表の注記どおり12:20頃から）。分野の絞り込みは「一覧」の選択と共通。</p>'
        '<div class="dayctl"><label><input type="checkbox" id="ow"> 希望リストのゼミだけ</label><label><input type="checkbox" id="sp"> 終わった日も表示</label></div>'
        '<div id="dayview"></div>'
        '<details><summary class="hint">原本（個別説明会一覧表・2026/10/19時点）の頁を見る</summary>'
        + "".join('<img src="%s" alt="個別説明会一覧表 %d頁目" loading="lazy">' % (fn, i + 1) for i, fn in enumerate(imgs)) + '</details></div>'
        '<div id="v-front">' + (front or '<p class="empty">前書き（p.1〜3）は書き起こし中。</p>') + '</div>'
        '<div class="cmpbar"><button class="btn" data-a="tab" data-t="cmp">並べて比較へ</button><button class="btn" data-a="tab" data-t="wish">希望リストへ</button>'
        '<button class="btn" data-a="tab" data-t="list">一覧へ</button></div>'
        '<p class="src">出典：' + esc(d.get("source", "")) + '。説明文は原文のまま（PDFの段組みによる改行の整形と、部首などの互換文字を通常の字に揃えたのみ）。'
        '画像だけの頁は目で書き起こした（〔判読不能〕〔?〕は読み取れなかった箇所）。※印は原本の一覧表の印。'
        '希望リストと比較の選択は、この端末のブラウザの中だけに保存される。</p>')
    html = ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow"><meta name="theme-color" content="#22303C"><title>専門演習を比べる</title>'
            + FONTS + '<style>' + HUB_CSS + ZCSS + '</style>'
            "<script>try{if(localStorage.getItem('studyhub_theme')==='light')document.documentElement.setAttribute('data-theme','light')}catch(e){}</script>"
            '</head><body><div class="wrap">' + body + '</div>'
            '<script type="application/json" id="zemi-data">' + js_data + '</script><script>' + APP + '</script></body></html>')
    atomicio.write_text(os.path.join(OUT, "index.html"), html)
    print("zemi: %d 名 / 日程画像 %d 枚 -> public/zemi/" % (len(teachers), len(imgs)))


if __name__ == "__main__":
    build()
