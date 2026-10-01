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
    }


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

  /* 3. 今日の復習（講義日から 1・3・7・14・30 日。復習するたびに次の間隔へ） */
  var RK='studyhub_review_v1', st={}; try{st=JSON.parse(get(RK)||'{}')}catch(e){st={}}
  function due(l){
    var k=l.course+'#'+l.round, s=st[k]||{n:0,last:l.date};
    if(s.n>=D.intervals.length) return null;
    return {k:k,s:s,d:new Date(day0(s.last).getTime()+D.intervals[s.n]*DAY)};
  }
  function renderReview(){
    var list=[];
    D.lectures.forEach(function(l){var x=due(l); if(x&&x.d<=today) list.push({l:l,x:x})});
    list.sort(function(a,b){return a.x.d-b.x.d});
    var rh='';
    list.forEach(function(o){
      var late=Math.round((today-o.x.d)/DAY);
      rh+=row(md(day0(o.l.date)),o.l.course+' 第'+o.l.round+'回',(o.x.s.n+1)+'回目の復習'+(late?' ∧ '+late+'日遅れ':''),
        o.l.url,late?'soon':'','<button class="done" data-k="'+esc(o.x.k)+'" type="button">済</button>');
    });
    document.getElementById('dash-review').innerHTML=rh||'<div class="empty">今日の復習はない</div>';
    document.getElementById('dash-rv-count').textContent=list.length+' 回分';
    document.querySelectorAll('#dash-review .done').forEach(function(b){
      b.addEventListener('click',function(ev){
        ev.preventDefault(); ev.stopPropagation();
        var k=b.getAttribute('data-k'), l=D.lectures.filter(function(x){return x.course+'#'+x.round===k})[0];
        var s=st[k]||{n:0,last:l.date}; st[k]={n:s.n+1,last:ymd(today)}; set(RK,JSON.stringify(st)); renderReview();
      });
    });
  }
  renderReview();

  /* 4. 検索の入口 */
  var f=document.getElementById('dash-q');
  if(f) f.addEventListener('submit',function(ev){
    ev.preventDefault(); var q=document.getElementById('dash-qi').value.trim();
    location.href='search/'+(q?'?q='+encodeURIComponent(q):'');
  });
  document.getElementById('dash-date').textContent=ymd(today)+' ('+W[wd(today)]+')';
})();
"""


def _panel(pid, label, name, count_id=""):
    c = '<span class="c" id="%s"></span>' % count_id if count_id else ""
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
        + _panel("dash-cl", "CLASS", "今日と明日の授業") + '<div id="dash-classes"></div></div>'
        + _panel("dash-dl", "DUE", "締切（14日以内）", "dash-dl-count") + '<div id="dash-deadlines"></div></div>'
        + _panel("dash-rv", "REVIEW", "今日の復習", "dash-rv-count") + '<div id="dash-review"></div>'
        '<p class="hint">講義の日から1・3・7・14・30日後に、その回をもう一度読む。読んだら「済」を押すと次の間隔へ進む。'
        '記録はこの端末の中だけに残る。</p></div>'
        + _panel("dash-sr", "FIND", "講義まとめを横断して探す")
        + '<form class="qbox" id="dash-q" role="search"><input id="dash-qi" type="search" placeholder="語句（空白で区切ると全部を含むもの）"'
        ' aria-label="講義まとめを検索" autocomplete="off"><button type="submit">FIND</button></form>'
        '<p class="hint">' + esc(term.get("name", "")) + 'を含む全学期の講義まとめが対象。検索はこの端末の中だけで行い、語句は外部に送らない。</p></div>'
        + '</div></section>'
        '<script type="application/json" id="dash-data">' + js_data + '</script>'
        '<script>' + JS + '</script>')
