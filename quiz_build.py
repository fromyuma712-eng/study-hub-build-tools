# -*- coding: utf-8 -*-
"""小テスト対策の頁（自己採点式・単一 HTML）を、問題の JSON から組む。

問題の正本は quiz_src/<code>_questions.json（科目名を含むので git 管理外）。出力は講義資料の置き場の
<科目>/小テスト対策.html で、site_config の MANIFEST に載せると build.py がハブへ配る。

    python -X utf8 quiz_build.py <code> <出力HTML> "<試験の日時 YYYY-MM-DDTHH:MM>" "<題>"

問題の形（1問）:
  {"id","round","kind":"概念|計算|コード読解","topic","type":"single|multi|num","q","code","choices","a","tol","explain"}
  a は single なら選択肢の番号（0始まり）、multi なら番号の列、num なら数値。数式は $...$（MathJax）。
仕様は記憶の「自己採点式HTML学習ツール」に従う（正解の統一表示・ブックマーク・ホームの分離・カウントダウン）。
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import hub_style  # noqa: E402

CSS = r"""
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.75;
  background-image:radial-gradient(var(--dot) 1px,transparent 1px);background-size:24px 24px}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px 80px}
a{color:var(--ink)}
.top{display:flex;align-items:center;gap:12px;font-family:var(--mono);font-size:12px;letter-spacing:.12em;color:var(--faint)}
.top a{text-decoration:none;color:var(--faint)}
h1{font-size:22px;font-weight:500;margin:10px 0 4px}
.meta{color:var(--muted);font-size:13.5px}
.cd{font-family:var(--mono);color:var(--ember-text)}
.bar{height:4px;background:var(--line);margin:10px 0 2px;position:relative}
.bar i{position:absolute;left:0;top:0;bottom:0;background:var(--ember)}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 10px;border-bottom:1px solid var(--line-strong);padding-bottom:8px}
.tabs button,.flt button,.btn{font:inherit;font-size:13px;background:none;color:var(--muted);border:1px solid var(--line);padding:4px 12px;min-height:36px;cursor:pointer}
.tabs button.on,.flt button.on{border-color:var(--ember);color:var(--ink)}
.flt{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}
.flt .lb{font-family:var(--mono);font-size:11px;color:var(--faint);letter-spacing:.12em;align-self:center;margin-right:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(340px,100%),1fr));gap:12px;align-items:stretch;margin-top:10px}
@media (max-width:420px){.grid{grid-template-columns:1fr}}
.q{position:relative;border:1px solid var(--line);padding:14px 16px 12px;display:flex;flex-direction:column;min-width:0;overflow-wrap:anywhere}
.q::before,.q::after{content:"";position:absolute;width:5px;height:5px;background:var(--line-strong);top:-3px}
.q::before{left:-3px}.q::after{right:-3px}
.q.ok{border-color:rgba(120,190,140,.7)}.q.ng{border-color:var(--ember)}
.qh{display:flex;flex-wrap:wrap;gap:8px;align-items:baseline;font-family:var(--mono);font-size:11.5px;color:var(--faint);letter-spacing:.06em}
.qh .k{border:1px solid var(--line);padding:0 6px}
.qt{margin:6px 0 8px}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.6;background:var(--glow);border:1px solid var(--line);padding:8px 10px;overflow-x:auto;margin:0 0 8px;white-space:pre}
.ch{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.ch label{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);padding:6px 8px;cursor:pointer;min-height:36px}
.ch label.right{border-color:rgba(120,190,140,.9);background:rgba(120,190,140,.10)}
.ch label.wrong{border-color:var(--ember)}
.ch input{margin-top:6px}
.ch .no{font-family:var(--mono);font-size:12px;color:var(--faint);min-width:1.2em}
.num input{font:inherit;font-family:var(--mono);background:none;color:var(--ink);border:1px solid var(--line-strong);padding:6px 8px;width:10em}
.foot{margin-top:auto;display:flex;gap:8px;align-items:center;padding-top:8px}
.btn.go{border-color:var(--line-strong);color:var(--ink)}
.bm{width:40px;padding:0}
.bm.on{border-color:var(--ember);color:var(--ember-text)}
.res{font-family:var(--mono);font-size:12.5px}
.ex{border-top:1px dashed var(--line);margin-top:8px;padding-top:8px;font-size:14px}
.ex .ans{color:var(--ember-text);margin-bottom:4px}
.home p,.home li{max-width:46em}
.home .st{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:12px 0}
.home .st div{border:1px solid var(--line);padding:8px 10px}
.home .st b{display:block;font-family:var(--mono);font-size:22px;font-weight:500}
.empty{color:var(--faint);padding:20px 0}
mjx-container[display="true"]{display:block;max-width:100%;overflow-x:auto;overflow-y:hidden}
mjx-container:not([display="true"]){display:inline-block;max-width:100%;overflow-x:auto;overflow-y:hidden;vertical-align:middle;scrollbar-width:thin}
"""

JS = r"""
(function(){
var D=JSON.parse(document.getElementById('qd').textContent), Q=D.questions, KEY='quiz_'+D.code+'_v1';
var st={}; try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){st={}}
st.done=st.done||{}; st.bm=st.bm||{};
function save(){try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
var view='home', fr='all', fk='all', shown={};
function typeset(el){if(window.MathJax&&MathJax.typesetPromise)MathJax.typesetPromise([el]).catch(function(){})}
function cdown(){
  var t=new Date(D.exam), ms=t-new Date(), el=document.getElementById('cd'); if(!el)return;
  if(ms<=0){el.textContent='試験の時刻を過ぎた';return}
  var d=Math.floor(ms/864e5), h=Math.floor(ms%864e5/36e5), m=Math.floor(ms%36e5/6e4);
  el.textContent='あと '+(d?d+'日':'')+h+'時間'+(d?'':m+'分');
}
function prog(){
  var n=Q.length, ok=Q.filter(function(q){return st.done[q.id]===1}).length, tried=Object.keys(st.done).length;
  var p=Math.round(ok/n*100);
  document.getElementById('pb').style.width=p+'%';
  document.getElementById('pt').textContent='正解 '+ok+' / '+n+'（'+p+'%）・解いた '+tried+' 問・ブックマーク '+Object.keys(st.bm).length+' 問';
}
function ansText(q){
  if(q.type==='num') return String(q.a);
  if(q.type==='single') return (q.a+1)+'. '+q.choices[q.a];
  return q.a.map(function(i){return (i+1)+'. '+q.choices[i]}).join(' ／ ');
}
function card(q){
  var h='<article class="q'+(st.done[q.id]===1&&shown[q.id]?' ok':st.done[q.id]===0&&shown[q.id]?' ng':'')+'" id="'+q.id+'">'
   +'<div class="qh"><span>'+esc(q.id.toUpperCase())+'</span><span class="k">第'+q.round+'回</span><span class="k">'+esc(q.kind)+'</span><span>'+esc(q.topic)+'</span></div>'
   +'<div class="qt">'+esc(q.q)+'</div>'+(q.code?'<pre>'+esc(q.code)+'</pre>':'');
  if(q.type==='num') h+='<div class="num"><input type="text" inputmode="decimal" aria-label="答え" data-i="'+q.id+'"></div>';
  else h+='<div class="ch">'+q.choices.map(function(c,i){return '<label><input type="'+(q.type==='multi'?'checkbox':'radio')+'" name="'+q.id+'" value="'+i+'"><span class="no">'+(i+1)+'</span><span>'+esc(c)+'</span></label>'}).join('')+'</div>'
     +(q.type==='multi'?'<div class="res">当てはまるものをすべて選ぶ</div>':'');
  h+='<div class="foot"><button class="btn go" data-a="grade" data-q="'+q.id+'">採点</button>'
   +'<button class="btn bm'+(st.bm[q.id]?' on':'')+'" data-a="bm" data-q="'+q.id+'" aria-label="ブックマーク">'+(st.bm[q.id]?'★':'☆')+'</button>'
   +'<span class="res" id="r-'+q.id+'"></span></div><div class="exw" id="e-'+q.id+'"></div></article>';
  return h;
}
function grade(id){
  var q=Q.filter(function(x){return x.id===id})[0], el=document.getElementById(id), ok;
  if(q.type==='num'){
    var v=parseFloat((el.querySelector('input').value||'').replace(/[^0-9.\-eE]/g,''));
    if(isNaN(v)){document.getElementById('r-'+id).textContent='数値を入れる';return}
    ok=Math.abs(v-q.a)<=(q.tol||1e-9);
  } else {
    var sel=[].slice.call(el.querySelectorAll('input:checked')).map(function(i){return +i.value}).sort();
    if(!sel.length){document.getElementById('r-'+id).textContent='選んでから採点する';return}
    var ans=q.type==='single'?[q.a]:q.a.slice().sort();
    ok=sel.length===ans.length&&sel.every(function(v,i){return v===ans[i]});
    [].slice.call(el.querySelectorAll('label')).forEach(function(l,i){l.classList.remove('right','wrong');
      if(ans.indexOf(i)>=0)l.classList.add('right'); else if(sel.indexOf(i)>=0)l.classList.add('wrong')});
  }
  st.done[id]=ok?1:0; shown[id]=1; save();
  el.classList.remove('ok','ng'); el.classList.add(ok?'ok':'ng');
  document.getElementById('r-'+id).textContent=ok?'正解':'不正解';
  var ex=document.getElementById('e-'+id);
  ex.innerHTML='<div class="ex"><div class="ans">正解：'+esc(ansText(q))+'</div>'+esc(q.explain)+'</div>';
  typeset(ex); prog();
}
function list(){
  var L=Q.filter(function(q){return (fr==='all'||String(q.round)===fr)&&(fk==='all'||q.kind===fk)&&(view!=='bm'||st.bm[q.id])&&(view!=='miss'||st.done[q.id]===0)});
  return L.length?'<div class="grid">'+L.map(card).join('')+'</div>':'<div class="empty">'+(view==='bm'?'ブックマークした問題はない。':view==='miss'?'間違えた問題はない。':'該当する問題はない。')+'</div>';
}
function flt(){
  var R=[];Q.forEach(function(q){if(R.indexOf(q.round)<0)R.push(q.round)});R.sort();
  var K=[];Q.forEach(function(q){if(K.indexOf(q.kind)<0)K.push(q.kind)});
  return '<div class="flt"><span class="lb">ROUND</span><button data-a="fr" data-v="all" class="'+(fr==='all'?'on':'')+'">すべて</button>'
    +R.map(function(r){return '<button data-a="fr" data-v="'+r+'" class="'+(fr===String(r)?'on':'')+'">第'+r+'回</button>'}).join('')+'</div>'
    +'<div class="flt"><span class="lb">KIND</span><button data-a="fk" data-v="all" class="'+(fk==='all'?'on':'')+'">すべて</button>'
    +K.map(function(k){return '<button data-a="fk" data-v="'+esc(k)+'" class="'+(fk===k?'on':'')+'">'+esc(k)+'</button>'}).join('')+'</div>';
}
function home(){
  var by={};Q.forEach(function(q){by[q.kind]=(by[q.kind]||0)+1});
  return '<div class="home"><div class="st"><div><b>'+Q.length+'</b>問</div>'+Object.keys(by).map(function(k){return '<div><b>'+by[k]+'</b>'+esc(k)+'</div>'}).join('')+'</div>'
   +'<p>'+esc(D.about)+'</p><ul>'+D.tips.map(function(t){return '<li>'+esc(t)+'</li>'}).join('')+'</ul>'
   +'<p class="meta">問題は講義まとめ・スライド・教員配布のノートブックをもとにした自作で、実際の小テストの問題ではない。記録（正解・ブックマーク）はこの端末の中にだけ残る。</p>'
   +'<p><button class="btn go" data-a="view" data-v="all">問題を解く →</button> <button class="btn" data-a="reset">記録を消す</button></p></div>';
}
function render(){
  ['home','all','miss','bm'].forEach(function(v){var b=document.getElementById('t-'+v);if(b)b.className=view===v?'on':''});
  var m=document.getElementById('main');
  m.innerHTML=view==='home'?home():flt()+list();
  typeset(m); prog();
}
document.addEventListener('click',function(e){
  var b=e.target.closest('[data-a]'); if(!b)return; var a=b.getAttribute('data-a');
  if(a==='grade'){grade(b.getAttribute('data-q'));return}
  if(a==='bm'){var id=b.getAttribute('data-q');if(st.bm[id])delete st.bm[id];else st.bm[id]=1;save();b.classList.toggle('on',!!st.bm[id]);b.textContent=st.bm[id]?'★':'☆';prog();return}
  if(a==='view'){view=b.getAttribute('data-v');shown={}}
  else if(a==='fr'){fr=b.getAttribute('data-v')}
  else if(a==='fk'){fk=b.getAttribute('data-v')}
  else if(a==='reset'){if(!confirm('正解とブックマークの記録を消す。よいか。'))return;st={done:{},bm:{}};save()}
  else return;
  render(); window.scrollTo(0,0);
});
cdown(); setInterval(cdown,60000); render();
})();
"""

MATHJAX = ('<script>MathJax={tex:{inlineMath:[["$","$"]],displayMath:[["$$","$$"]]},svg:{fontCache:"global"},'
           'startup:{typeset:false}};</script>'
           '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>')


def build(code, out, exam, title):
    d = json.load(open(os.path.join(ROOT, "quiz_src", "%s_questions.json" % code), encoding="utf-8"))
    meta = json.load(open(os.path.join(ROOT, "quiz_src", "%s_meta.json" % code), encoding="utf-8"))
    data = {"code": code, "exam": exam, "questions": d["questions"],
            "about": meta["about"], "tips": meta["tips"]}
    js_data = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    e = html.escape
    page = ('<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title>%s<style>%s%s</style>%s'
            '<script>try{var t=localStorage.getItem("studyhub_theme");if(t)document.documentElement.setAttribute("data-theme",t)}catch(e){}</script></head><body><div class="wrap">'
            '<div class="top"><a href="../">← STUDY HUB</a><span>QUIZ ∧ %s</span></div>'
            '<h1>%s</h1><div class="meta">%s ／ 試験 %s <span class="cd" id="cd"></span></div>'
            '<div class="bar"><i id="pb"></i></div><div class="meta" id="pt"></div>'
            '<div class="tabs"><button id="t-home" data-a="view" data-v="home">ホーム</button>'
            '<button id="t-all" data-a="view" data-v="all">問題</button>'
            '<button id="t-miss" data-a="view" data-v="miss">間違えた問題</button>'
            '<button id="t-bm" data-a="view" data-v="bm">ブックマーク復習</button></div>'
            '<div id="main"></div></div>'
            '<script type="application/json" id="qd">%s</script><script>%s</script></body></html>'
            % (e(title), hub_style.FONTS, hub_style.CSS, CSS, MATHJAX, e(code.upper()), e(title),
               e(meta["scope"]), e(exam.replace("T", " ")), js_data, JS))
    open(out, "w", encoding="utf-8").write(page)
    print("quiz: %s %d 問 -> %s" % (code, len(d["questions"]), out))


if __name__ == "__main__":
    build(*sys.argv[1:5])
