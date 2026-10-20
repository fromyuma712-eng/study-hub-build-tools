# -*- coding: utf-8 -*-
"""ハブの先頭に置くダッシュボード（TODAY）を組む（2026/10/2）。

    from dashboard import dashboard_section
    html = dashboard_section(C, headings, manifest)

- 今日・明日の授業（時間割とオンデマンド配信）、近い締切、今日の復習、全文検索への入口を一面に出す。
- データ（時間割・締切・講義日）は site_config.py（非公開）から読み、ページに JSON として埋め込む。
  「今日」の判定はブラウザで行うので、毎日作り直さなくても表示は正しい（ビルドの決定性も保つ）。
- 復習の記録は端末の localStorage に置く（外部には送らない。端末間では共有されない）。
- 外部のサービス・スクリプトは使わない。

先行事例（2026/10/2 調査）:
- 期限が近いもの・手を付けるべきものを科目横断で一面に出す（Obsidian の Course Command Center）
- 学んだ日から間隔を広げて復習日を出す（Notion の学生向けダッシュボードの 1・7・14 日など）
- 計画→実行→振り返りを支え、表現を単純に揃え、プライバシーを守る（学習分析ダッシュボードの設計指針）
"""
import json
import os
import re

from hub_style import esc, sect_head


def _anchors(headings):
    """科目名 → {回: 見出しの id}。見出しが「第N回」で始まるものだけ。"""
    out = {}
    for e in headings:
        m = {}
        for h in e.get("headings", []):
            r = re.match(r"\s*第\s*(\d+)\s*回", h.get("text", ""))
            if r and int(r.group(1)) not in m:
                m[int(r.group(1))] = h.get("anchor", "")
        out[e["course"]] = m
    return out


def _urls(manifest):
    """科目名 → 講義まとめの URL（ハブからの相対）。中身を持たない科目は無し。"""
    out = {}
    for it in manifest:
        if it.get("offline") or it.get("url") or not it.get("dest"):
            continue
        out.setdefault(it["course"], it["dest"].replace("/index.html", "/"))
    return out


def data(C, headings, manifest):
    urls, anc = _urls(manifest), _anchors(headings)

    def link(course, rnd=None):
        u = urls.get(course)
        if not u:
            return None
        a = anc.get(course, {}).get(rnd) if rnd else None
        return u + ("#" + a if a else "")

    return {
        "term": getattr(C, "TERM", None),
        "periods": {str(k): v for k, v in getattr(C, "PERIODS", {}).items()},
        "timetable": [dict(t, url=link(t["course"])) for t in getattr(C, "TIMETABLE", [])],
        "ondemand": [dict(t, url=link(t["course"])) for t in getattr(C, "ON_DEMAND", [])],
        "cancelled": [list(x) for x in getattr(C, "CANCELLED", [])],
        "deadlines": [dict(d, url=link(d["course"]) if d.get("course") else None)
                      for d in getattr(C, "DEADLINES", [])],
        "lectures": [{"course": c, "round": r, "date": d, "url": link(c, r)}
                     for c, r, d in getattr(C, "LECTURES", [])],
        "intervals": list(getattr(C, "REVIEW_INTERVALS", [1, 3, 7, 14, 30])),
        "notices": _notices(C, link),
        "zemi": _zemi(),
    }


def _notices(C, link):
    """各科目の、講義日のある最新回のお知らせ（notices.json。apply_notices.py と同じ正本）。"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notices.json")
    if not os.path.isfile(p):
        return []
    courses = json.load(open(p, encoding="utf-8")).get("courses", {})
    held = {}
    for c, r, d in getattr(C, "LECTURES", []):
        if str(r) in courses.get(c, {}) and (c not in held or r > held[c][0]):
            held[c] = (r, d)
    out = []
    for c, (r, d) in held.items():
        n = courses[c][str(r)]
        if not (n.get("next") or n.get("quiz") or n.get("tasks")):
            continue
        out.append({"course": c, "round": r, "date": d, "url": link(c, r),
                    "next": n.get("next"), "quiz": n.get("quiz"), "tasks": n.get("tasks") or []})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def _zemi():
    """専門演習の個別説明会（zemi.json の schedule。zemi_build と同じ正本）。無ければ空。"""
    root = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(os.path.join(root, "zemi.json")):
        return None
    import zemi_build
    d = json.load(open(os.path.join(root, "zemi.json"), encoding="utf-8"))
    sd = zemi_build.schedule_data(d.get("schedule"))
    if not sd["sessions"]:
        return None
    return {"t": {str(t["page"]): [t["name"], t["field"]] for t in d["teachers"]},
            "s": [[x["date"], x["start"], x["end"], x["label"], x["place"] or "", x["mode"], x["p"]] for x in sd["sessions"]]}


CSS = r"""
.dash{margin:0 0 36px}
.dgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-top:8px}
.panel{position:relative;border:1px solid var(--line);padding:14px 18px 12px;min-height:120px}
.panel::before,.panel::after,.panel .bl,.panel .br{content:"";position:absolute;width:5px;height:5px;background:var(--line-strong);pointer-events:none}
.panel::before{top:-3px;left:-3px}.panel::after{top:-3px;right:-3px}.panel .bl{bottom:-3px;left:-3px}.panel .br{bottom:-3px;right:-3px}
.panel.hot::before{background:var(--ember)}
.ph{display:flex;align-items:center;gap:10px;min-height:28px;margin-bottom:6px}
.ph .n{font-size:14px;color:var(--muted)}
.ph .c{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--faint);letter-spacing:.06em}
.li{display:grid;grid-template-columns:4.6em 1fr auto;gap:10px;align-items:center;min-height:44px;padding:4px 0;
  border-top:1px solid var(--line);text-decoration:none;color:inherit;font-size:15px;line-height:1.5}
.li:first-of-type{border-top:none}
a.li:hover{background:var(--glow)}
.li .t{font-family:var(--mono);font-size:12px;color:var(--faint);letter-spacing:.04em}
.li .s{font-size:12px;color:var(--faint)}
.li.soon .t{color:var(--ember-text)}
.li.nt{align-items:start;padding:8px 0}
.li .nb{display:flex;flex-direction:column;gap:2px}
.li .nb b{font-weight:500;font-size:15px}
.li .nb .s{font-size:13px;line-height:1.6;color:var(--muted);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.li .nb .s.q{color:var(--ember-text)}
.li.past{opacity:.55}
.li .x{font-family:var(--mono);font-size:12px;color:var(--faint);white-space:nowrap}
.empty{font-size:14px;color:var(--faint);padding:8px 0}
.daylbl{font-family:var(--mono);font-size:12px;letter-spacing:.14em;color:var(--faint);margin:8px 0 2px}
.done{font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--faint);background:none;
  border:1px solid var(--line);min-height:36px;padding:0 10px;cursor:pointer;border-radius:0;
  transition:transform .42s var(--spring),border-color .2s,color .2s}
.done:hover{border-color:var(--line-strong);color:var(--ink)}
.done:active{transform:scale(.94);transition-duration:.07s}
.qbox{display:flex;gap:8px;margin-top:4px}
.qbox input{flex:1;min-height:44px;background:transparent;color:var(--ink);border:1px solid var(--line-strong);
  border-radius:0;padding:0 12px;font:inherit;font-size:16px}
.qbox input:focus{outline:none;border-color:var(--ink)}
.qbox button{min-height:44px;padding:0 14px;background:none;border:1px solid var(--line-strong);color:var(--ink);
  font-family:var(--mono);font-size:12px;letter-spacing:.12em;cursor:pointer;border-radius:0}
.hint{font-size:12px;color:var(--faint);margin-top:8px;line-height:1.6}
.more{display:block;width:100%;min-height:44px;margin-top:6px;background:none;border:1px solid var(--line);color:var(--muted);
  font-family:var(--mono);font-size:12px;letter-spacing:.08em;cursor:pointer;border-radius:0}
.more:hover{border-color:var(--line-strong);color:var(--ink)}
@media (max-width:560px){.dgrid{grid-template-columns:1fr}.li{grid-template-columns:4.2em 1fr auto}}
"""

JS = r"""
(function(){
  var el=document.getElementById('dash-data'); if(!el) return;
  var D=JSON.parse(el.textContent), DAY=864e5;
  function get(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function set(k,v){try{localStorage.setItem(k,v)}catch(e){}}
  function ymd(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
  function day0(s){var p=s.split('-');return new Date(+p[0],+p[1]-1,+p[2])}
  function at(s){var p=s.split('T'),d=day0(p[0]),t=(p[1]||'00:00').split(':');d.setHours(+t[0],+t[1]);return d}
  function md(d){return (d.getMonth()+1)+'/'+d.getDate()}
  var W='月火水木金土日', now=new Date(), today=day0(ymd(now));
  function wd(d){return (d.getDay()+6)%7}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function row(t,main,sub,url,cls,extra){
    var tag=url?'a':'div', h=url?' href="'+esc(url)+'"':'';
    return '<'+tag+' class="li'+(cls?' '+cls:'')+'"'+h+'><span class="t">'+t+'</span><span>'+esc(main)
      +(sub?'<br><span class="s">'+esc(sub)+'</span>':'')+'</span>'+(extra||'<span></span>')+'</'+tag+'>';
  }
  var inTerm=D.term&&today>=day0(D.term.start)&&today<=day0(D.term.end);

  /* 1. 今日・明日の授業 */
  function classes(d){
    var w=wd(d), s=ymd(d), out=[];
    if(!inTerm) return out;
    D.timetable.forEach(function(c){ if(c.day===w) out.push({t:D.periods[c.period]||'',p:c.period+'限',c:c}) });
    D.ondemand.forEach(function(c){ if(c.day===w) out.push({t:c.time,p:'配信',c:c}) });
    out.forEach(function(o){ o.off=D.cancelled.some(function(x){return x[0]===o.c.course&&x[1]===s}) });
    return out.sort(function(a,b){return a.t<b.t?-1:1});
  }
  var h='';
  [[today,'今日'],[new Date(today.getTime()+DAY),'明日']].forEach(function(p){
    var list=classes(p[0]);
    h+='<div class="daylbl">'+p[1]+' '+md(p[0])+'（'+W[wd(p[0])]+'）</div>';
    if(!list.length){h+='<div class="empty">授業なし</div>';return}
    list.forEach(function(o){ h+=row(o.t,o.c.course,o.p+(o.off?' ∧ 休講':''),o.off?null:o.c.url,o.off?'past':'') });
  });
  if(!inTerm) h='<div class="empty">学期の期間外</div>';
  document.getElementById('dash-classes').innerHTML=h;

  /* 2. 締切（過ぎて1日以内〜これから14日） */
  var DL=D.deadlines.map(function(x){return {d:at(x.at),x:x}}).filter(function(o){
    return o.d.getTime()>now.getTime()-DAY && o.d.getTime()<now.getTime()+14*DAY}).sort(function(a,b){return a.d-b.d});
  var dh='';
  DL.forEach(function(o){
    var left=Math.ceil((o.d-now)/DAY), past=o.d<now;
    var t=md(o.d)+' '+('0'+o.d.getHours()).slice(-2)+':'+('0'+o.d.getMinutes()).slice(-2);
    dh+=row(md(o.d),o.x.label,(o.x.course||'')+' ∧ '+t,o.x.url,past?'past':(left<=3?'soon':''),
      '<span class="x">'+(past?'過ぎた':(left<=1?'あと1日以内':'あと'+left+'日'))+'</span>');
  });
  document.getElementById('dash-deadlines').innerHTML=dh||'<div class="empty">14日以内の締切はない</div>';
  document.getElementById('dash-dl-count').textContent=DL.filter(function(o){return o.d>=now}).length+' 件';
  if(DL.some(function(o){return o.d>=now&&o.d-now<3*DAY})) document.getElementById('dash-dl').classList.add('hot');

  /* 2b. 授業からのお知らせ（各科目の最新回の、次回・小テスト・課題）。小テストのある科目を先に、5科目まで */
  var NT=(D.notices||[]).slice().sort(function(a,b){return (b.quiz?1:0)-(a.quiz?1:0)||(a.date<b.date?1:-1)}), ntOpen=false;
  function renderNotices(){
    var nh='', LIM=5;
    NT.forEach(function(o,i){
      if(!ntOpen&&i>=LIM) return;
      var lines='';
      if(o.quiz) lines+='<span class="s q">小テスト：'+esc(o.quiz)+'</span>';
      if(o.next) lines+='<span class="s">次回：'+esc(o.next)+'</span>';
      o.tasks.forEach(function(t){ lines+='<span class="s">課題：'+esc(t)+'</span>' });
      nh+='<a class="li nt'+(o.quiz?' soon':'')+'" href="'+(o.url||'#')+'"><span class="t">'+md(day0(o.date))+'</span>'
        +'<span class="nb"><b>'+esc(o.course)+' 第'+o.round+'回</b>'+lines+'</span><span></span></a>';
    });
    if(NT.length>LIM) nh+='<button class="more" id="nt-more" type="button">'+(ntOpen?'先頭の'+LIM+'科目だけにする':'残り'+(NT.length-LIM)+'科目も表示')+'</button>';
    document.getElementById('dash-notices').innerHTML=nh||'<div class="empty">お知らせはない</div>';
    var mb=document.getElementById('nt-more'); if(mb) mb.addEventListener('click',function(){ntOpen=!ntOpen; renderNotices()});
  }
  renderNotices();
  document.getElementById('dash-nt-count').textContent=NT.length+' 科目';

  /* 2c. 専門演習の個別説明会（終わっていない回。希望リスト＝zemi 頁の zemi_wish_v1 に入れたゼミを先に） */
  (function(){
    var Z=D.zemi, box=document.getElementById('dash-zm'); if(!Z||!box) return;
    var wish=[]; try{wish=JSON.parse(get('zemi_wish_v1')||'[]')}catch(e){wish=[]}
    function endOf(x){var e=at(x[0]+'T'+(x[2]||x[1]||'23:59'));if(!x[2]&&x[1])e=new Date(e.getTime()+60*6e4);return e}
    var up=Z.s.filter(function(x){return endOf(x)>now});
    var W2=up.filter(function(x){return wish.indexOf(x[6])>=0}), seen={}, nextW=[];
    W2.forEach(function(x){if(!seen[x[6]]){seen[x[6]]=1;nextW.push(x)}});
    var list=wish.length?nextW:up, td=ymd(today), nToday=up.filter(function(x){return x[0]===td}).length;
    var zh='';
    list.slice(0,5).forEach(function(x){
      var t=Z.t[x[6]]||['',''], wi=wish.indexOf(x[6]), d=day0(x[0]);
      var tm=x[1]?(x[1]+(x[3]==='昼休み'&&x[5]==='対面'?'頃':'')+(x[2]?'–'+x[2]:'〜')):'';
      zh+=row(md(d),t[0]+(wi>=0?'（第'+(wi+1)+'希望）':''),'（'+W[wd(d)]+'）'+tm+(x[3]?' '+x[3]:'')+' ∧ '+(x[5]==='対面'?x[4]:'リアルタイム配信'+(x[4]?'（学内視聴 '+x[4]+'）':'')),
        'zemi/#z'+x[6],x[0]===td?'soon':'');
    });
    if(!up.length) zh='<div class="empty">個別説明会の期間は終わった</div>';
    else if(!list.length) zh='<div class="empty">希望リストのゼミに、これからの回はない</div>';
    document.getElementById('dash-zemi').innerHTML=zh;
    document.getElementById('dash-zm-count').textContent=up.length?'今日あと '+nToday+' 回':'';
    document.getElementById('dash-zm-hint').textContent=wish.length
      ?'希望リストに入れた '+wish.length+' ゼミの、次の回を時刻順に並べた。'
      :'これからの回を時刻順に並べた。ゼミ比較の頁で「希望に入れる」を押すと、そのゼミの回だけをここに出す。';
  })();

  /* 3. 今日の復習（講義日から 1・3・7・14・30 日。復習するたびに次の間隔へ） */
  var RK='studyhub_review_v1', st={}; try{st=JSON.parse(get(RK)||'{}')}catch(e){st={}}
  function due(l){
    var k=l.course+'#'+l.round, s=st[k]||{n:0,last:l.date};
    if(s.n>=D.intervals.length) return null;
    return {k:k,s:s,d:new Date(day0(s.last).getTime()+D.intervals[s.n]*DAY)};
  }
  var rvOpen=false;
  function renderReview(){
    var list=[];
    D.lectures.forEach(function(l){var x=due(l); if(x&&x.d<=today) list.push({l:l,x:x})});
    list.sort(function(a,b){return a.x.d-b.x.d});
    var rh='', shown=0, LIM=6;
    list.forEach(function(o,i){
      if(!rvOpen&&i>=LIM) return; shown++;
      var late=Math.round((today-o.x.d)/DAY);
      rh+=row(md(day0(o.l.date)),o.l.course+' 第'+o.l.round+'回',(o.x.s.n+1)+'回目の復習'+(late?' ∧ '+late+'日遅れ':''),
        o.l.url,late?'soon':'','<button class="done" data-k="'+esc(o.x.k)+'" type="button">済</button>');
    });
    if(list.length>LIM) rh+='<button class="more" id="rv-more" type="button">'+(rvOpen?'先頭の'+LIM+'回分だけにする':'残り'+(list.length-LIM)+'回分も表示')+'</button>';
    document.getElementById('dash-review').innerHTML=rh||'<div class="empty">今日の復習はない</div>';
    document.getElementById('dash-rv-count').textContent=list.length+' 回分';
    var mb=document.getElementById('rv-more'); if(mb) mb.addEventListener('click',function(){rvOpen=!rvOpen; renderReview()});
    document.querySelectorAll('#dash-review .done').forEach(function(b){
      b.addEventListener('click',function(ev){
        ev.preventDefault(); ev.stopPropagation();
        var k=b.getAttribute('data-k'), l=D.lectures.filter(function(x){return x.course+'#'+x.round===k})[0];
        var s=st[k]||{n:0,last:l.date}; st[k]={n:s.n+1,last:ymd(today)}; set(RK,JSON.stringify(st)); renderReview();
      });
    });
  }
  renderReview();

  /* 3b. 最近の講義まとめ（講義日の新しい順に8回分） */
  var rc=D.lectures.slice().sort(function(a,b){return a.date<b.date?1:(a.date>b.date?-1:(a.course<b.course?-1:1))}).slice(0,8), rch='';
  rc.forEach(function(l){
    var ago=Math.round((today-day0(l.date))/DAY);
    rch+=row(md(day0(l.date)),l.course+' 第'+l.round+'回',ago<=0?'今日':ago+'日前',l.url,ago<=2?'soon':'');
  });
  document.getElementById('dash-recent').innerHTML=rch||'<div class="empty">まだない</div>';
  document.getElementById('dash-rc-count').textContent=D.lectures.length+' 回分';

  /* 4. 検索の入口 */
  var f=document.getElementById('dash-q');
  if(f) f.addEventListener('submit',function(ev){
    ev.preventDefault(); var q=document.getElementById('dash-qi').value.trim();
    location.href='search/'+(q?'?q='+encodeURIComponent(q):'');
  });
  /* 「/」で検索欄へ（入力中は何もしない） */
  document.addEventListener('keydown',function(ev){
    var t=ev.target&&ev.target.tagName;
    if(ev.key==='/'&&!ev.metaKey&&!ev.ctrlKey&&!ev.altKey&&t!=='INPUT'&&t!=='TEXTAREA'&&t!=='SELECT'){
      var i=document.getElementById('dash-qi'); if(i){ev.preventDefault(); i.focus(); i.scrollIntoView({block:'center'})}
    }
  });
  document.getElementById('dash-date').textContent=ymd(today)+' ('+W[wd(today)]+')';
})();
"""


def _panel(pid, label, name, count_id="", link=""):
    c = '<span class="c" id="%s"></span>' % count_id if count_id else (link or "")
    return ('<div class="panel" id="%s"><span class="bl"></span><span class="br"></span>'
            '<div class="ph"><span class="lbl">%s</span><span class="n">%s</span>%s</div>' % (pid, label, esc(name), c))


def dashboard_section(C, headings, manifest):
    if not getattr(C, "TIMETABLE", None) and not getattr(C, "DEADLINES", None):
        return ""
    js_data = json.dumps(data(C, headings, manifest), ensure_ascii=False).replace("</", "<\\/")
    term = getattr(C, "TERM", {}) or {}
    return (
        '<style>' + CSS + '</style>'
        '<section class="dash" id="today">' + sect_head("TODAY", "今日の勉強", '<span id="dash-date"></span>')
        + '<div class="dgrid">'
        + _panel("dash-cl", "CLASS", "今日と明日の授業", link='<a class="c" href="#timetable" style="text-decoration:none">時間割 ↓</a>') + '<div id="dash-classes"></div></div>'
        + _panel("dash-dl", "DUE", "締切（14日以内）", "dash-dl-count") + '<div id="dash-deadlines"></div></div>'
        + _panel("dash-nt", "NOTICE", "授業からのお知らせ", "dash-nt-count") + '<div id="dash-notices"></div>'
        '<p class="hint">各科目の最新回で述べられた次回・小テスト・課題（小テストのある科目が先）。全文と Claude の TIPS は各回の末尾にある。</p></div>'
        + ((_panel("dash-zm", "SEMINAR", "ゼミ個別説明会", "dash-zm-count") + '<div id="dash-zemi"></div>'
            '<p class="hint"><span id="dash-zm-hint"></span> <a href="zemi/#sched">全日程 →</a>　<a href="zemi/">ゼミを比べる →</a></p></div>')
           if _zemi() else "")
        + _panel("dash-rv", "REVIEW", "今日の復習", "dash-rv-count") + '<div id="dash-review"></div>'
        '<p class="hint">講義の日から1・3・7・14・30日後に、その回をもう一度読む。読んだら「済」を押すと次の間隔へ進む。'
        '記録はこの端末の中だけに残る。</p></div>'
        + _panel("dash-rc", "RECENT", "最近の講義まとめ", "dash-rc-count") + '<div id="dash-recent"></div></div>'
        + _panel("dash-sr", "FIND", "講義まとめを横断して探す")
        + '<form class="qbox" id="dash-q" role="search"><input id="dash-qi" type="search" placeholder="語句（空白で区切ると全部を含むもの）"'
        ' aria-label="講義まとめを検索" autocomplete="off"><button type="submit">FIND</button></form>'
        '<p class="hint">' + esc(term.get("name", "")) + 'を含む全学期の講義まとめが対象。検索はこの端末の中だけで行い、語句は外部に送らない。「/」キーで検索欄へ移る。</p></div>'
        + '</div><p class="hint" style="margin-top:10px"><a href="zemi/">専門演習（ゼミ）を比べる →</a>'
        '　2027年度の配属先を、分野・自動検出タグ・全文検索で絞り込み、並べて比較する（申込 11/10〜11/12）。</p></section>'
        '<script type="application/json" id="dash-data">' + js_data + '</script>'
        '<script>' + JS + '</script>')


# ---------------------------------------------------------------------------------------------
# 時間割（週の格子）。ハブのトップ、TODAY の下に置く（2026/10/4）
# ---------------------------------------------------------------------------------------------
DAYS = "月火水木金土日"

TT_CSS = r"""
.tt{display:grid;grid-template-columns:5.4em repeat(5,minmax(0,1fr));border-top:1px solid var(--line);border-left:1px solid var(--line);margin-top:8px}
.tt>*{border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:8px 10px;min-width:0}
.tt .th{display:flex;align-items:center;gap:8px;min-height:44px;font-family:var(--mono);font-size:13px;letter-spacing:.14em;color:var(--faint)}
.tt .th::before{content:"";width:5px;height:5px;background:var(--line-strong);flex:none}
.tt .th.corner::before{display:none}
.tt .th.today{color:var(--ember-text)}
.tt .th.today::before{background:var(--ember)}
.tt .tr{display:flex;flex-direction:column;justify-content:center;font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--faint);line-height:1.5}
.tt .tr b{font-weight:500;color:var(--ink);font-size:13px}
.tt .tc{min-height:84px;display:flex;flex-direction:column;gap:6px}
.tt .tc.empty{min-height:56px}
.tt .tc.today{background:var(--glow)}
.tt .tc.now{box-shadow:inset 3px 0 0 var(--ember)}
.tt .tl{display:none;font-family:var(--mono);font-size:12px;letter-spacing:.08em;color:var(--faint)}
.tt .ti{display:block;text-decoration:none;color:inherit;transition:transform .42s var(--spring)}
a.ti:active{transform:scale(.97);transition-duration:.07s}
a.ti:hover .tn{text-decoration:underline;text-underline-offset:3px}
.tt .tk{display:block;font-family:var(--mono);font-size:12px;letter-spacing:.1em;color:var(--faint)}
.tt .tn{display:block;font-size:15px;line-height:1.45;color:var(--ink)}
.tt .tm{display:block;font-family:var(--mono);font-size:12px;letter-spacing:.04em;color:var(--faint);margin-top:2px}
.tt .tc.now .tk{color:var(--ember-text)}
.tt .ti.off .tn{color:var(--muted)}
.tt .ti.cx .tn{text-decoration:line-through}
.tod{margin-top:14px}
.tod .th2{display:flex;flex-wrap:wrap;align-items:center;gap:6px 12px;min-height:30px}
.tod .oi2{display:grid;grid-template-columns:5em 1fr auto;gap:10px;align-items:center;min-height:46px;padding:6px 4px;border-top:1px solid var(--line);
  text-decoration:none;color:inherit}
a.oi2:hover{background:var(--glow)}
.tod .oi2 .k2{font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--faint)}
.tod .oi2 .m2{font-family:var(--mono);font-size:12px;color:var(--faint);white-space:nowrap}
.tnote{font-size:13px;color:var(--faint);margin-top:8px;line-height:1.7}
@media (max-width:760px){
  .tt{grid-template-columns:1fr;border-left:none}
  .tt>*{grid-column:auto!important;grid-row:auto!important;order:var(--o);border-left:none;border-right:none;padding:8px 4px}
  .tt .tr,.tt .th.corner{display:none}
  .tt .th{min-height:40px;margin-top:12px;border-bottom:1px solid var(--line-strong);font-size:14px}
  .tt .tc{min-height:0;opacity:1}
  .tt .tc.empty{display:none}
  .tt .tl{display:block}
  .tod .oi2{grid-template-columns:4em 1fr}.tod .oi2 .m2{grid-column:2}
}
"""

TT_JS = r"""
(function(){
  var g=document.getElementById('timetable'); if(!g) return;
  var now=new Date(), wd=(now.getDay()+6)%7;
  function ymd(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
  var today=ymd(now), min=now.getHours()*60+now.getMinutes();
  g.querySelectorAll('[data-day="'+wd+'"]').forEach(function(e){e.classList.add('today')});
  g.querySelectorAll('.tc[data-day="'+wd+'"]').forEach(function(c){
    var t=(c.getAttribute('data-t')||'').split(':'); if(t.length<2) return;
    var s=(+t[0])*60+(+t[1]); if(min>=s&&min<s+90) c.classList.add('now');
  });
  g.querySelectorAll('.ti[data-cx]').forEach(function(i){
    if(i.getAttribute('data-cx').split(' ').indexOf(today)>=0) i.classList.add('cx');
  });
})();
"""


def timetable_section(C, manifest, progress):
    tt = getattr(C, "TIMETABLE", None)
    if not tt:
        return ""
    periods = getattr(C, "PERIODS", {})
    term = getattr(C, "TERM", {}) or {}
    info = {}
    for it in manifest:
        info.setdefault(it["course"], it)
    cancel = {}
    for course, d in getattr(C, "CANCELLED", []):
        cancel.setdefault(course, []).append(d)

    def item(course, sub=""):
        it = info.get(course)
        code = it["code"] if it else ""
        href = None
        if it and not it.get("offline") and not it.get("url") and it.get("dest"):
            href = it["dest"].replace("/index.html", "/")
        meta = []
        if progress.get(course):
            meta.append("%d / %d" % progress[course])
        if cancel.get(course):
            meta.append("休講 " + "・".join("%d/%d" % (int(x[5:7]), int(x[8:10])) for x in sorted(cancel[course])))
        if sub:
            meta.insert(0, sub)
        cls = "ti" + (" off" if it and it.get("offline") else "")
        attrs = ' data-cx="%s"' % " ".join(sorted(cancel[course])) if cancel.get(course) else ""
        inner = ('<span class="tk">%s</span><span class="tn">%s</span>' % (esc(code), esc(course))
                 + ('<span class="tm">%s</span>' % esc(" ∧ ".join(meta)) if meta else ""))
        if href:
            return '<a class="%s" href="%s"%s>%s</a>' % (cls, esc(href), attrs, inner)
        return '<div class="%s"%s>%s</div>' % (cls, attrs, inner)

    maxp = max(t["period"] for t in tt)
    ndays = 5
    cells = ['<div class="th corner" style="grid-column:1;grid-row:1;--o:-1"></div>']
    for d in range(ndays):
        cells.append('<div class="th" data-day="%d" style="grid-column:%d;grid-row:1;--o:%d">%s<span class="d2"></span></div>'
                     % (d, d + 2, d * 10, DAYS[d] + '<span style="letter-spacing:0">曜</span>'))
    for p in range(1, maxp + 1):
        cells.append('<div class="tr" style="grid-column:1;grid-row:%d;--o:-1"><b>%d限</b>%s</div>'
                     % (p + 1, p, esc(periods.get(p, ""))))
    for d in range(ndays):
        for p in range(1, maxp + 1):
            here = [t for t in tt if t["day"] == d and t["period"] == p]
            o = d * 10 + p
            lab = '<span class="tl">%s ∧ %d限 ∧ %s</span>' % (DAYS[d], p, esc(periods.get(p, "")))
            body = "".join(item(t["course"]) for t in here)
            cells.append('<div class="tc%s" data-day="%d" data-t="%s" style="grid-column:%d;grid-row:%d;--o:%d">%s%s</div>'
                         % ("" if here else " empty", d, esc(periods.get(p, "")), d + 2, p + 1, o, lab if here else "", body))
    od = getattr(C, "ON_DEMAND", [])
    odh = ""
    if od:
        rows = "".join(
            ('<%s class="oi2"%s><span class="k2">%s</span><span>%s</span><span class="m2">毎週%s曜 %s 配信</span></%s>'
             % (("a" if (info.get(o["course"]) and not info[o["course"]].get("offline") and info[o["course"]].get("dest")) else "div"),
                (' href="%s"' % esc(info[o["course"]]["dest"].replace("/index.html", "/")))
                if (info.get(o["course"]) and not info[o["course"]].get("offline") and info[o["course"]].get("dest")) else "",
                esc(info[o["course"]]["code"]) if info.get(o["course"]) else "",
                esc(o["course"]), DAYS[o["day"]], esc(o["time"]),
                ("a" if (info.get(o["course"]) and not info[o["course"]].get("offline") and info[o["course"]].get("dest")) else "div")))
            for o in od)
        odh = ('<div class="tod"><div class="th2"><span class="lbl">ON DEMAND</span><span class="nm" style="font-size:14px;'
               'color:var(--muted)">遠隔（オンデマンド）</span></div>' + rows + '</div>')
    meta = esc(term.get("name", "")) + ((" ∧ %s〜%s" % (term["start"][5:].replace("-", "/"), term["end"][5:].replace("-", "/")))
                                        if term.get("start") and term.get("end") else "")
    return ('<style>' + TT_CSS + '</style><section class="dash" id="timetable">'
            + sect_head("TIMETABLE", "時間割", meta)
            + '<div class="tt">' + "".join(cells) + '</div>' + odh
            + '<p class="tnote">科目の名前を押すと、その科目のまとめへ入る。数字は、まとめた回／全回。'
              '<span style="color:var(--ember-text)">■</span> は今日の曜日と、いま授業中のコマ。休講の日は、その日の欄に取り消し線が付く。</p>'
              '</section><script>' + TT_JS + '</script>')
