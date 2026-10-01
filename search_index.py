# -*- coding: utf-8 -*-
"""講義まとめを横断する全文検索（FIND の面）を作る（2026/10/2）。

    python -X utf8 search_index.py      # build.py・generate_extra_pages.py の後に実行

- 各頁を見出し（h2・h3）ごとの節に分け、public/search/index.json に書く。
- public/search/index.html は検索の面。索引を読み込み、検索は端末の中だけで行う（外部のサービス・
  スクリプトを使わない。索引も講義まとめと同じく認証の内側に置かれる）。
- 先行事例：Pagefind・Lunr などの静的サイト内検索（外部に語句を送らない）。規模が小さいので
  ライブラリは使わず、正規化した文字列の部分一致で探す（日本語の分かち書きが要らない）。
"""
import html as _html
import importlib.util
import json
import os
import re

import atomicio

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, "public")
spec = importlib.util.spec_from_file_location("buildmod", os.path.join(ROOT, "build.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
C = B.C


def text_of(fragment):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    s = re.sub(r"<svg\b.*?</svg>", " ", s, flags=re.S | re.I)   # 図の中の文字は除き、図の結論（figcaption）は残す
    s = re.sub(r"<br\s*/?>|</(div|p|li|tr|h[1-6]|figcaption)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t　]+", " ", s)
    return re.sub(r"\s*\n\s*", "\n", s).strip()


def sections(page_html):
    s = re.sub(r'<!-- OBSERVATORY-SKIN:(\w+)[^>]*-->.*?<!-- /OBSERVATORY-SKIN:\1 -->', "", page_html, flags=re.S)
    m = re.search(r"<body[^>]*>(.*)</body>", s, re.S)
    s = m.group(1) if m else s
    s = re.sub(r'<div class="note small">.*?</div>', " ", s, flags=re.S)   # 作成方針は検索対象にしない
    s = re.sub(r'<button[^>]*>.*?</button>', " ", s, flags=re.S)
    heads = list(re.finditer(r'<(h[23])([^>]*)>(.*?)</\1>', s, re.S))
    out = []
    h2 = ""
    for i, hm in enumerate(heads):
        idm = re.search(r'\bid="([^"]+)"', hm.group(2))
        title = text_of(hm.group(3))
        if hm.group(1) == "h2":
            h2 = title
        body = s[hm.end(): heads[i + 1].start() if i + 1 < len(heads) else len(s)]
        t = text_of(body)
        if not t:
            continue
        out.append({"a": idm.group(1) if idm else "", "h": title if hm.group(1) == "h2" else (h2 + " ／ " + title), "t": t})
    return out


def build_index():
    dyn = set(getattr(C, "DYNAMIC_APPS", []))
    docs = []
    for it in B.MANIFEST:
        src = it.get("src")
        if not src or it.get("offline") or it.get("dest") in dyn:
            continue
        path = os.path.join(B.SRC_BASE, src)
        if not os.path.isfile(path):
            continue
        url = it["dest"].replace("/index.html", "/")
        for sec in sections(open(path, encoding="utf-8").read()):
            docs.append({"c": it["course"], "k": it["code"], "s": B.semester_label(B.semester_key(it))[1],
                         "u": url + ("#" + sec["a"] if sec["a"] else ""), "h": sec["h"], "t": sec["t"]})
    return docs


CSS = r"""
.sbox{display:flex;gap:8px;margin:0 0 10px}
.sbox input{flex:1;min-height:48px;background:transparent;color:var(--ink);border:1px solid var(--line-strong);border-radius:0;
  padding:0 14px;font:inherit;font-size:17px}
.sbox input:focus{outline:none;border-color:var(--ink)}
.sstat{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--faint);min-height:24px;margin-bottom:8px}
.fil{min-height:44px;margin:0 0 14px;padding:0 10px;background:var(--ground);color:var(--ink);border:1px solid var(--line);
  border-radius:0;font:inherit;font-size:14px;max-width:100%}
.hit{display:block;border-top:1px solid var(--line);padding:12px 4px 14px;text-decoration:none;color:inherit;
  transition:background-color .42s var(--settle)}
.hit:hover{background:var(--glow)}
.hit .hc{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--faint)}
.hit .hh{font-size:15px;color:var(--ink);margin:2px 0 4px}
.hit .hs{font-size:14px;color:var(--muted);line-height:1.7}
.hit mark{background:none;color:var(--ink);font-weight:600;box-shadow:inset 0 -2px 0 var(--ember)}
"""

JS = r"""
(function(){
  var q=document.getElementById('q'), out=document.getElementById('hits'), stat=document.getElementById('stat'),
      fil=document.getElementById('fil'), IDX=null, NORM=null, course='';
  function fold(ch){var c=ch.normalize('NFKC').toLowerCase();
    return c.replace(/[ァ-ヶ]/g,function(k){return String.fromCharCode(k.charCodeAt(0)-0x60)})}
  /* 文字ごとに正規化し、元の位置との対応を持つ（抜粋の位置合わせのため） */
  function norm(s){var n='',map=[];for(var i=0;i<s.length;i++){var f=fold(s[i]);for(var j=0;j<f.length;j++){n+=f[j];map.push(i)}}return {n:n,map:map}}
  function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function load(cb){
    if(IDX) return cb();
    stat.textContent='索引を読み込み中…';
    fetch('index.json',{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){
      IDX=d; NORM=d.map(function(x){return {h:norm(x.h).n,t:norm(x.t)}});
      var cs=[]; d.forEach(function(x){if(cs.indexOf(x.c)<0)cs.push(x.c)});
      fil.innerHTML='<option value="">すべての科目</option>'+cs.map(function(c){return '<option value="'+esc(c)+'">'+esc(c)+'</option>'}).join('');
      fil.addEventListener('change',function(){course=fil.value; run()});
      cb();
    }).catch(function(){stat.textContent='索引を読めなかった（再読み込みしてください）'});
  }
  function snippet(x,nt,terms){
    var p=-1; terms.forEach(function(t){var i=nt.n.indexOf(t); if(i>=0&&(p<0||i<p))p=i});
    var o=p<0?0:nt.map[p], a=Math.max(0,o-50), b=Math.min(x.t.length,o+110), s=x.t.slice(a,b).replace(/\n/g,' ');
    var ns=norm(s), marks=[];
    terms.forEach(function(t){var i=0; while((i=ns.n.indexOf(t,i))>=0){marks.push([ns.map[i],ns.map[i+t.length-1]+1]); i+=t.length}});
    marks.sort(function(u,v){return u[0]-v[0]});
    var h='',k=0; marks.forEach(function(m){ if(m[0]<k) return; h+=esc(s.slice(k,m[0]))+'<mark>'+esc(s.slice(m[0],m[1]))+'</mark>'; k=m[1] });
    return (a>0?'…':'')+h+esc(s.slice(k))+(b<x.t.length?'…':'');
  }
  function run(){
    var raw=q.value.trim(); history.replaceState(null,'',raw?'?q='+encodeURIComponent(raw):location.pathname);
    if(!raw){out.innerHTML='';stat.textContent=IDX?IDX.length+' 節を検索できる':'';return}
    load(function(){
      var terms=norm(raw).n.split(/\s+/).filter(Boolean), res=[];
      IDX.forEach(function(x,i){
        if(course&&x.c!==course) return;
        var n=NORM[i], sc=0;
        for(var j=0;j<terms.length;j++){
          var t=terms[j], c=n.t.n.split(t).length-1, hc=n.h.indexOf(t)>=0?5:0;
          if(!c&&!hc) return; sc+=c+hc;
        }
        res.push({x:x,n:n,sc:sc});
      });
      res.sort(function(a,b){return b.sc-a.sc});
      stat.textContent=res.length+' 件'+(res.length>80?'（上位80件を表示）':'');
      out.innerHTML=res.slice(0,80).map(function(r){
        return '<a class="hit" href="../'+esc(r.x.u)+'"><div class="hc">'+esc(r.x.k)+' ∧ '+esc(r.x.c)+' ∧ '+esc(r.x.s)+'</div>'
          +'<div class="hh">'+esc(r.x.h)+'</div><div class="hs">'+snippet(r.x,r.n.t,terms)+'</div></a>';
      }).join('');
    });
  }
  var timer=null;
  q.addEventListener('input',function(){clearTimeout(timer);timer=setTimeout(run,180)});
  document.getElementById('sf').addEventListener('submit',function(e){e.preventDefault();run()});
  var p=new URLSearchParams(location.search).get('q'); if(p){q.value=p} load(run);
})();
"""


def build_page(n):
    body = ('<style>' + CSS + '</style>'
            '<section class="sect" style="margin-top:0">'
            + B.sect_head("FIND", "講義まとめを横断して探す", "%d 節" % n)
            + '<form class="sbox" id="sf" role="search"><input id="q" type="search" autocomplete="off" autofocus '
            'placeholder="語句（空白で区切ると全部を含むもの）" aria-label="検索語"></form>'
            '<div class="sstat" id="stat"></div><select class="fil" id="fil" aria-label="科目で絞り込む"></select><div id="hits"></div>'
            '<p class="note" style="margin-top:20px">検索はこの端末の中だけで行い、語句は外部に送らない。'
            'カタカナとひらがな、全角と半角、大文字と小文字は区別しない。</p></section>'
            '<script>' + JS + '</script>')
    spec_html = "<span class=\"sp\"><b>%d</b> SECTIONS</span><span class=\"sp\">LOCAL SEARCH</span>" % n
    return B.page(body, spec_html, face="find")


def main():
    docs = build_index()
    os.makedirs(os.path.join(PUBLIC, "search"), exist_ok=True)
    atomicio.write_text(os.path.join(PUBLIC, "search", "index.json"),
                        json.dumps(docs, ensure_ascii=False, separators=(",", ":")))
    atomicio.write_text(os.path.join(PUBLIC, "search", "index.html"), build_page(len(docs)))
    size = os.path.getsize(os.path.join(PUBLIC, "search", "index.json"))
    print("search: %d 節 / 索引 %.1f MB -> public/search/" % (len(docs), size / 1e6))


if __name__ == "__main__":
    main()
