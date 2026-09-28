# -*- coding: utf-8 -*-
"""Generate single-file KPI dashboard HTML from pipeline/data.json.

Renders two stacked sections: WeChat (top) and DingTalk (bottom). Each section
has its own month/day tabs, person filter, KPI cards, charts, and issue table.
Colors are keyed by person name so the same individual shows the same color in
both sources.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "outputs")
HTML_OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "index.html")

with open(os.path.join(OUT, "data.json"), encoding="utf-8") as f:
    DATA = json.load(f)

DATA_JSON = json.dumps(DATA, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>群服务响应 KPI 看板（微信 + 钉钉）</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js"></script>
<style>
:root{
  --bg:#0f1420; --panel:#171e2e; --panel2:#1d2637; --line:#2a3550;
  --txt:#e8ecf5; --muted:#8b96ad; --accent:#4f8cff; --good:#3ecf8e; --warn:#f5a524; --bad:#f0566a;
  --dt-accent:#a06bff;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;padding:20px 26px 60px}
h1{font-size:22px;font-weight:600}
h2{font-size:18px;font-weight:600;display:flex;align-items:center;gap:10px}
.sub{color:var(--muted);font-size:12.5px;margin-top:4px}
.head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;margin-bottom:14px}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:22px}
.summary .box{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:12.5px;color:var(--muted)}
.summary .box b{color:var(--txt);font-size:14px}
.src-block{border:1px solid var(--line);border-radius:14px;padding:16px 18px 20px;margin-bottom:26px;background:linear-gradient(180deg,rgba(79,140,255,.04),transparent 200px)}
.src-block.dt{background:linear-gradient(180deg,rgba(160,107,255,.05),transparent 200px)}
.src-block .tag{display:inline-block;padding:3px 10px;border-radius:12px;background:var(--accent);color:#fff;font-size:11.5px;font-weight:600;letter-spacing:.5px}
.src-block.dt .tag{background:var(--dt-accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:14px 0 18px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:24px;font-weight:700;margin-top:4px}
.kpi .l{color:var(--muted);font-size:12px}
.kpi .v.good{color:var(--good)} .kpi .v.warn{color:var(--warn)} .kpi .v.bad{color:var(--bad)} .kpi .v.acc{color:var(--accent)}
.src-block.dt .kpi .v.acc{color:var(--dt-accent)}
.tabs{display:flex;gap:8px;margin:6px 0 14px}
.tab{padding:7px 18px;border-radius:20px;border:1px solid var(--line);background:var(--panel);color:var(--muted);cursor:pointer;font-size:13.5px}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.src-block.dt .tab.on{background:var(--dt-accent);border-color:var(--dt-accent)}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
select{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:13.5px}
.chip{padding:5px 13px;border-radius:16px;border:1px solid var(--line);background:var(--panel);cursor:pointer;font-size:12.5px;color:var(--muted);margin-right:6px;display:inline-block}
.chip.on{color:#fff;border-color:transparent}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:1fr 1fr}
@media(max-width:980px){.g2{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card h3{font-size:14px;font-weight:600;margin-bottom:8px;color:#cfd8ea}
.chart{width:100%;height:300px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:500;font-size:12px}
td.msg{white-space:normal;max-width:420px;color:#c6cfdf}
.pill{padding:2px 9px;border-radius:10px;font-size:11.5px}
.pill.res{background:rgba(62,207,142,.15);color:var(--good)}
.pill.unres{background:rgba(240,86,106,.15);color:var(--bad)}
.pill.wait{background:rgba(245,165,36,.15);color:var(--warn)}
.pcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin-bottom:16px}
.pcard{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:12px 14px}
.pcard .nm{font-weight:600;font-size:15px}
.pcard .row{display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);margin-top:6px}
.pcard .row b{color:var(--txt)}
.note{margin-top:22px;color:var(--muted);font-size:12px;line-height:1.85;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.hide{display:none}
.empty{color:var(--muted);padding:20px;text-align:center;font-size:13px}
</style>
</head>
<body>
<div class="head">
  <div>
    <h1>群服务响应 KPI 看板</h1>
    <div class="sub">微信 + 钉钉 双数据源　·　生成时间 <span id="gen"></span></div>
  </div>
</div>

<div class="summary" id="summary"></div>

<!-- ===== WeChat section ===== -->
<section class="src-block" id="sec-wx">
  <h2><span class="tag">微信</span> 微信群服务响应</h2>
  <div class="sub" id="wx-range"></div>
  <div class="kpis" id="wx-kpis"></div>
  <div class="tabs" id="wx-tabs">
    <div class="tab on" data-v="month">月维度</div>
    <div class="tab" data-v="day">日维度</div>
  </div>
  <div class="bar"><span style="color:var(--muted);font-size:13px">人员：</span><span id="wx-chips"></span></div>
  <div id="wx-v-month">
    <div class="bar"><span style="color:var(--muted);font-size:13px">月份：</span><select id="wx-msel"></select></div>
    <div class="card" style="margin-bottom:14px"><h3>人员月度汇总</h3><div style="overflow-x:auto"><table id="wx-mtable"></table></div></div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><h3>每日发言 / 回复趋势</h3><div id="wx-c1" class="chart"></div></div>
      <div class="card"><h3>每日问题响应：已确认解决 vs 跟进中</h3><div id="wx-c2" class="chart"></div></div>
    </div>
    <div class="grid g2">
      <div class="card"><h3>人均响应问题数 & 解决率</h3><div id="wx-c3" class="chart"></div></div>
      <div class="card"><h3>平均首响时长 & 30分钟及时率</h3><div id="wx-c4" class="chart"></div></div>
    </div>
  </div>
  <div id="wx-v-day" class="hide">
    <div class="bar"><span style="color:var(--muted);font-size:13px">日期：</span><select id="wx-dsel"></select></div>
    <div class="pcards" id="wx-pcards"></div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><h3>当日各人员发言 / 回复问题</h3><div id="wx-d1" class="chart" style="height:260px"></div></div>
      <div class="card"><h3>当日问题解决分布</h3><div id="wx-d2" class="chart" style="height:260px"></div></div>
    </div>
    <div class="card"><h3>当日问题 / 请求明细（含响应与解决状态）</h3><div style="overflow-x:auto"><table id="wx-dtable"></table></div></div>
  </div>
</section>

<!-- ===== DingTalk section ===== -->
<section class="src-block dt" id="sec-dt">
  <h2><span class="tag">钉钉</span> 钉钉群服务响应</h2>
  <div class="sub" id="dt-range"></div>
  <div class="kpis" id="dt-kpis"></div>
  <div class="tabs" id="dt-tabs">
    <div class="tab on" data-v="month">月维度</div>
    <div class="tab" data-v="day">日维度</div>
  </div>
  <div class="bar"><span style="color:var(--muted);font-size:13px">人员：</span><span id="dt-chips"></span></div>
  <div id="dt-v-month">
    <div class="bar"><span style="color:var(--muted);font-size:13px">月份：</span><select id="dt-msel"></select></div>
    <div class="card" style="margin-bottom:14px"><h3>人员月度汇总</h3><div style="overflow-x:auto"><table id="dt-mtable"></table></div></div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><h3>每日发言 / 回复趋势</h3><div id="dt-c1" class="chart"></div></div>
      <div class="card"><h3>每日问题响应：已确认解决 vs 跟进中</h3><div id="dt-c2" class="chart"></div></div>
    </div>
    <div class="grid g2">
      <div class="card"><h3>人均响应问题数 & 解决率</h3><div id="dt-c3" class="chart"></div></div>
      <div class="card"><h3>平均首响时长 & 30分钟及时率</h3><div id="dt-c4" class="chart"></div></div>
    </div>
  </div>
  <div id="dt-v-day" class="hide">
    <div class="bar"><span style="color:var(--muted);font-size:13px">日期：</span><select id="dt-dsel"></select></div>
    <div class="pcards" id="dt-pcards"></div>
    <div class="grid g2" style="margin-bottom:14px">
      <div class="card"><h3>当日各人员发言 / 回复问题</h3><div id="dt-d1" class="chart" style="height:260px"></div></div>
      <div class="card"><h3>当日问题解决分布</h3><div id="dt-d2" class="chart" style="height:260px"></div></div>
    </div>
    <div class="card"><h3>当日问题 / 请求明细（含响应与解决状态）</h3><div style="overflow-x:auto"><table id="dt-dtable"></table></div></div>
  </div>
</section>

<div class="note">
<b>口径说明（启发式 v2 · 双源）</b><br>
· <b>数据源</b>：微信 = SiverWXbot 群聊记忆 JSON（3 处目录合并去重）+ 桌面截图人工补录；钉钉 = <code>dws chat +chat-messages</code> 每日 18:00 增量抓取（按 messageId 去重后落 <code>pipeline/dingtalk_msgs.jsonl</code>）。<br>
· <b>关注人员</b>：陈景斯、郝天琪、何昕怡、张康宁、史敦兵、胡晟瑞、刘佳琪（两源共用名单，颜色一致）。<br>
· <b>「问题/请求」</b>：群内 @ 关注人员、或含求助/疑问关键词（麻烦、辛苦、看下、无法、怎么办、修复、报错…）的非关注人员消息。<br>
· <b>「回复/响应」</b>：关注人员在同一群内对该问题的首条回复。微信响应窗口 <b>8 小时</b>，钉钉放宽到 <b>24 小时</b>（钉钉群消息稀疏）。钉钉额外把「引用回复指向原提问人」也算作应答。<br>
· <b>「已确认解决」</b>：响应后微信 4 小时 / 钉钉 12 小时内出现解决信号（响应人：已处理/已修复/更新了/推送了…；或提出人：好了/收到/谢谢/可以了…）。<br>
· <b>「及时」</b>：首响 ≤ 30 分钟。<br>
· 纯致谢/确认消息（好的、谢谢、收到等）不计为问题。图片/文件等无文本消息不参与问题判定（除非同时 @ 了关注人）。
</div>

<script>
const DATA = __DATA__;
const PALETTE = ["#5470c6","#91cc75","#fac858","#ee6666","#73c0de","#9a60b4","#fc8452","#4f8cff","#3ecf8e","#f0566a","#a06bff","#3ec9c4"];
// Global color map: same person -> same color across both sections.
const ALL_PEOPLE = [...new Set([
  ...(DATA.sources.wechat.people||[]),
  ...(DATA.sources.dingtalk.people||[]),
])];
const COLORS = {};
ALL_PEOPLE.forEach((p,i)=>{ COLORS[p] = PALETTE[i % PALETTE.length]; });

document.getElementById('gen').textContent = DATA.generated;

// Header summary
(function renderSummary(){
  const wx = DATA.sources.wechat, dt = DATA.sources.dingtalk;
  const box = (label, s, extra) => `<div class="box">${label}<br><b>${s}</b>${extra?`<br><span style="font-size:11.5px">${extra}</span>`:''}</div>`;
  const wxRange = (wx.days && wx.days.length) ? (wx.days[0]+' ~ '+wx.days[wx.days.length-1]) : '—';
  const dtRange = (dt.days && dt.days.length) ? (dt.days[0]+' ~ '+dt.days[dt.days.length-1]) : '—';
  document.getElementById('summary').innerHTML = [
    box('微信 · 消息', wx.total_msgs||0, wxRange+'　·　'+(wx.groups||[]).length+' 个群'),
    box('微信 · 识别问题', wx.total_issues||0, '响应窗 '+wx.resp_window_h+'h　·　解决窗 '+wx.resolve_window_h+'h'),
    box('钉钉 · 消息', dt.total_msgs||0, dtRange+'　·　'+(dt.groups||[]).length+' 个群'),
    box('钉钉 · 识别问题', dt.total_issues||0, '响应窗 '+dt.resp_window_h+'h　·　解决窗 '+dt.resolve_window_h+'h'),
  ].join('');
})();

const charts = {};
function mk(id){
  const el = document.getElementById(id);
  if(!el) return null;
  if(charts[id]) charts[id].dispose();
  charts[id] = echarts.init(el);
  return charts[id];
}
const baseGrid = {left:44,right:20,top:36,bottom:30};
const axis = {axisLine:{lineStyle:{color:'#3a4763'}},axisLabel:{color:'#8b96ad'},splitLine:{lineStyle:{color:'#232d44'}}};

function mountSection(prefix, SRC){
  const PEOPLE = SRC.people || [];
  const state = {
    sel: new Set(PEOPLE),
    view: 'month',
    curMonth: null,
    curDay: null,
  };
  const $ = id => document.getElementById(prefix+'-'+id);

  const pd = (p,d) => SRC.per_pd[p+'|'+d] || {msgs:0,resp:0,resolved:0,unresolved:0,avg_rt:null,ontime:0};
  const inSel = p => state.sel.has(p);
  const monthOf = d => d.slice(0,7);
  const daysIn = m => (SRC.days||[]).filter(d=>monthOf(d)===m);
  const months = () => [...new Set((SRC.days||[]).map(monthOf))].sort();
  const issuesOfDay = d => (SRC.issues||[]).filter(i=>i.date===d);

  function aggPersonMonth(p,m){
    const a={msgs:0,resp:0,resolved:0,unresolved:0,ontime:0,rt:[]};
    daysIn(m).forEach(d=>{ const v=pd(p,d); a.msgs+=v.msgs; a.resp+=v.resp; a.resolved+=v.resolved; a.unresolved+=v.unresolved; a.ontime+=v.ontime; });
    (SRC.issues||[]).forEach(it=>{ if(it.responder===p && monthOf(it.date)===m && it.resp_min!=null) a.rt.push(it.resp_min); });
    a.avg_rt = a.rt.length? +(a.rt.reduce((x,y)=>x+y,0)/a.rt.length).toFixed(1) : null;
    a.ontimeRate = a.resp? Math.round(a.ontime/a.resp*100) : null;
    a.solveRate = a.resp? Math.round(a.resolved/a.resp*100) : null;
    return a;
  }

  function kpisGlobal(){
    let msgs=0,res=0,unres=0,rt=[];
    (SRC.days||[]).forEach(d=>PEOPLE.forEach(p=>{ if(!inSel(p))return; const v=pd(p,d);
      msgs+=v.msgs; res+=v.resolved; unres+=v.unresolved; }));
    (SRC.issues||[]).forEach(i=>{ if(i.responder&&inSel(i.responder)&&i.resp_min!=null) rt.push(i.resp_min); });
    const iss = (SRC.issues||[]).filter(i=>i.responder&&inSel(i.responder)).length;
    return {msgs, resp:iss, res, unres,
      rate: iss? Math.round(res/iss*100):0,
      avg: rt.length? (rt.reduce((a,b)=>a+b,0)/rt.length).toFixed(1):'-',
      ontime: rt.length? Math.round(rt.filter(x=>x<=SRC.ontime_min).length/rt.length*100):0};
  }

  function renderRange(){
    const days = SRC.days||[];
    $('range').textContent = days.length
      ? ('数据区间 '+days[0]+' ~ '+days[days.length-1]+'　·　消息 '+SRC.total_msgs+' 条　·　识别问题/请求 '+SRC.total_issues+' 个　·　覆盖群 '+(SRC.groups||[]).length+' 个')
      : '暂无数据';
  }

  function renderKpis(){
    const k = kpisGlobal();
    $('kpis').innerHTML = `
     <div class="kpi"><div class="l">关注人员发言</div><div class="v acc">${k.msgs}</div></div>
     <div class="kpi"><div class="l">识别问题/请求</div><div class="v">${k.resp}</div></div>
     <div class="kpi"><div class="l">已确认解决</div><div class="v good">${k.res}</div></div>
     <div class="kpi"><div class="l">跟进中/未确认</div><div class="v bad">${k.unres}</div></div>
     <div class="kpi"><div class="l">确认解决率</div><div class="v ${k.rate>=50?'good':(k.rate>=25?'warn':'bad')}">${k.rate}%</div></div>
     <div class="kpi"><div class="l">平均首响(分钟)</div><div class="v">${k.avg}</div></div>
     <div class="kpi"><div class="l">${SRC.ontime_min}分钟及时率</div><div class="v ${k.ontime>=70?'good':'warn'}">${k.ontime}%</div></div>`;
  }

  function buildChips(){
    const c = $('chips'); c.innerHTML = '';
    if(!PEOPLE.length){ c.innerHTML = '<span style="color:var(--muted);font-size:12.5px">（无关注人员配置）</span>'; return; }
    PEOPLE.forEach(p=>{
      const el = document.createElement('span');
      el.className = 'chip'+(state.sel.has(p)?' on':'');
      el.textContent = p;
      if(state.sel.has(p)) el.style.background = COLORS[p];
      el.onclick = ()=>{ if(state.sel.has(p)){ if(state.sel.size>1) state.sel.delete(p);} else state.sel.add(p); refresh(); };
      c.appendChild(el);
    });
  }

  function initSelects(){
    const ms = months();
    const msel = $('msel');
    if(ms.length){
      state.curMonth = ms[ms.length-1];
      msel.innerHTML = ms.map(m=>`<option>${m}</option>`).join('');
      msel.value = state.curMonth;
      msel.onchange = ()=>{ state.curMonth = msel.value; renderMonth(); };
    } else { msel.innerHTML = '<option>—</option>'; }
    const ds = $('dsel');
    const days = SRC.days||[];
    if(days.length){
      ds.innerHTML = days.slice().reverse().map(d=>`<option>${d}</option>`).join('');
      state.curDay = days[days.length-1];
      ds.value = state.curDay;
      ds.onchange = ()=>{ state.curDay = ds.value; renderDay(); };
    } else { ds.innerHTML = '<option>—</option>'; }
  }

  function renderMonth(){
    if(!state.curMonth){ $('mtable').innerHTML = '<tbody><tr><td class="empty">暂无数据</td></tr></tbody>'; return; }
    const m = state.curMonth, ds = daysIn(m);
    let rows = '';
    PEOPLE.filter(inSel).forEach(p=>{
      const a = aggPersonMonth(p,m);
      rows += `<tr><td><span style="color:${COLORS[p]};font-weight:600">${p}</span></td><td>${a.msgs}</td><td>${a.resp}</td>
        <td><span class="pill res">${a.resolved}</span></td><td><span class="pill unres">${a.unresolved}</span></td>
        <td>${a.solveRate==null?'-':a.solveRate+'%'}</td><td>${a.avg_rt==null?'-':a.avg_rt}</td>
        <td>${a.ontimeRate==null?'-':a.ontimeRate+'%'}</td></tr>`;
    });
    $('mtable').innerHTML = rows
      ? `<thead><tr><th>人员</th><th>发言数</th><th>响应问题数</th><th>已确认解决</th><th>跟进中</th><th>解决率</th><th>平均首响(分)</th><th>及时率</th></tr></thead><tbody>${rows}</tbody>`
      : '<tbody><tr><td class="empty">当前筛选无数据</td></tr></tbody>';

    const ps = PEOPLE.filter(inSel);
    const c1 = mk(prefix+'-c1');
    if(c1) c1.setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
      xAxis:{type:'category',data:ds.map(d=>d.slice(5)),...axis},yAxis:{type:'value',...axis},
      series:ps.map(p=>({name:p,type:'line',smooth:true,symbolSize:5,
        data:ds.map(d=>pd(p,d).msgs),lineStyle:{width:2},itemStyle:{color:COLORS[p]}}))});

    const resS = ds.map(d=>ps.reduce((s,p)=>s+pd(p,d).resolved,0));
    const unS = ds.map(d=>ps.reduce((s,p)=>s+pd(p,d).unresolved,0));
    const c2 = mk(prefix+'-c2');
    if(c2) c2.setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
      xAxis:{type:'category',data:ds.map(d=>d.slice(5)),...axis},yAxis:{type:'value',...axis},
      series:[{name:'已确认解决',type:'bar',stack:'a',data:resS,itemStyle:{color:'#3ecf8e'}},
              {name:'跟进中/未确认',type:'bar',stack:'a',data:unS,itemStyle:{color:'#f0566a'}}]});

    const c3 = mk(prefix+'-c3');
    if(c3) c3.setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:{...baseGrid,right:44},
      xAxis:{type:'category',data:ps,...axis},yAxis:[{type:'value',...axis},{type:'value',max:100,...axis,axisLabel:{color:'#8b96ad',formatter:'{value}%'}}],
      series:[{name:'响应问题数',type:'bar',data:ps.map(p=>aggPersonMonth(p,m).resp),itemStyle:{color:'#4f8cff'},barWidth:26},
              {name:'解决率',type:'line',yAxisIndex:1,data:ps.map(p=>aggPersonMonth(p,m).solveRate||0),itemStyle:{color:'#fac858'}}]});

    const c4 = mk(prefix+'-c4');
    if(c4) c4.setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:{...baseGrid,right:44},
      xAxis:{type:'category',data:ps,...axis},yAxis:[{type:'value',...axis},{type:'value',max:100,...axis,axisLabel:{color:'#8b96ad',formatter:'{value}%'}}],
      series:[{name:'平均首响(分)',type:'bar',data:ps.map(p=>aggPersonMonth(p,m).avg_rt||0),itemStyle:{color:'#73c0de'},barWidth:26},
              {name:'及时率',type:'line',yAxisIndex:1,data:ps.map(p=>aggPersonMonth(p,m).ontimeRate||0),itemStyle:{color:'#3ecf8e'}}]});
  }

  function renderDay(){
    if(!state.curDay){ $('pcards').innerHTML = '<div class="empty">暂无数据</div>'; return; }
    const d = state.curDay;
    let cards = '';
    PEOPLE.filter(inSel).forEach(p=>{
      const v = pd(p,d);
      const rate = v.resp? Math.round(v.resolved/v.resp*100):null;
      cards += `<div class="pcard" style="border-left-color:${COLORS[p]}">
        <div class="nm" style="color:${COLORS[p]}">${p}</div>
        <div class="row"><span>发言</span><b>${v.msgs}</b></div>
        <div class="row"><span>响应问题</span><b>${v.resp}</b></div>
        <div class="row"><span>已确认解决</span><b style="color:var(--good)">${v.resolved}</b></div>
        <div class="row"><span>跟进中</span><b style="color:var(--bad)">${v.unresolved}</b></div>
        <div class="row"><span>平均首响</span><b>${v.avg_rt==null?'-':v.avg_rt+'分'}</b></div>
        <div class="row"><span>解决率</span><b>${rate==null?'-':rate+'%'}</b></div></div>`;
    });
    $('pcards').innerHTML = cards || '<div class="empty">当前筛选无数据</div>';

    const ps = PEOPLE.filter(inSel);
    const d1 = mk(prefix+'-d1');
    if(d1) d1.setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
      xAxis:{type:'category',data:ps,...axis},yAxis:{type:'value',...axis},
      series:[{name:'发言',type:'bar',data:ps.map(p=>pd(p,d).msgs),itemStyle:{color:'#4f8cff'}},
              {name:'响应问题',type:'bar',data:ps.map(p=>pd(p,d).resp),itemStyle:{color:'#91cc75'}}]});

    const res = ps.reduce((s,p)=>s+pd(p,d).resolved,0), un = ps.reduce((s,p)=>s+pd(p,d).unresolved,0);
    const d2 = mk(prefix+'-d2');
    if(d2) d2.setOption({tooltip:{trigger:'item'},series:[{type:'pie',radius:['45%','70%'],
      data:[{name:'已确认解决',value:res,itemStyle:{color:'#3ecf8e'}},{name:'跟进中/未确认',value:un,itemStyle:{color:'#f0566a'}}],
      label:{color:'#aab4c8'}}]});

    const iss = issuesOfDay(d).filter(i=>i.responder&&inSel(i.responder));
    let rows = '';
    iss.forEach(i=>{
      const st = i.resolved?'<span class="pill res">已确认解决</span>':'<span class="pill wait">跟进中/未确认</span>';
      rows += `<tr><td>${i.ts.slice(11,16)}</td><td>${i.group||''}</td><td>${i.author||''}</td><td class="msg">${(i.text||'').replace(/</g,'&lt;')}</td>
        <td><span style="color:${COLORS[i.responder]}">${i.responder}</span></td>
        <td>${i.resp_min==null?'-':i.resp_min}</td><td>${st}</td></tr>`;
    });
    $('dtable').innerHTML = iss.length
      ? `<thead><tr><th>时间</th><th>群</th><th>提出人</th><th>问题/请求</th><th>响应人</th><th>首响(分)</th><th>状态</th></tr></thead><tbody>${rows}</tbody>`
      : `<tbody><tr><td class="empty">当日所选人员无识别到的问题/请求</td></tr></tbody>`;
  }

  function refresh(){
    buildChips(); renderKpis();
    if(state.view==='month') renderMonth(); else renderDay();
  }

  document.querySelectorAll('#'+prefix+'-tabs .tab').forEach(t=>t.onclick=()=>{
    document.querySelectorAll('#'+prefix+'-tabs .tab').forEach(x=>x.classList.remove('on'));
    t.classList.add('on');
    state.view = t.dataset.v;
    $(  'v-month').classList.toggle('hide', state.view!=='month');
    $('v-day').classList.toggle('hide', state.view!=='day');
    refresh();
  });

  renderRange(); initSelects(); refresh();
  return {refresh};
}

if(typeof echarts === 'undefined'){
  document.body.insertAdjacentHTML('afterbegin','<div style="color:#f0566a;padding:12px">ECharts 加载失败，请检查网络（图表依赖 CDN）。</div>');
}
const wxCtl = mountSection('wx', DATA.sources.wechat);
const dtCtl = mountSection('dt', DATA.sources.dingtalk);
window.addEventListener('resize',()=>Object.values(charts).forEach(c=>c && c.resize()));
</script>
</body>
</html>
"""

html_out = HTML.replace("__DATA__", DATA_JSON)
with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html_out)
with open(os.path.join(OUT, "dashboard.html"), "w", encoding="utf-8") as f:
    f.write(html_out)
print("written", HTML_OUT, len(html_out), "bytes")
