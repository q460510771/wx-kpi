# -*- coding: utf-8 -*-
"""Generate single-file KPI dashboard HTML from outputs/data.json."""
import json, os, datetime, sys

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
<title>微信群服务响应 KPI 看板</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js"></script>
<style>
:root{
  --bg:#0f1420; --panel:#171e2e; --panel2:#1d2637; --line:#2a3550;
  --txt:#e8ecf5; --muted:#8b96ad; --accent:#4f8cff; --good:#3ecf8e; --warn:#f5a524; --bad:#f0566a;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:"Segoe UI","Microsoft YaHei",system-ui,sans-serif;padding:20px 26px 60px}
h1{font-size:22px;font-weight:600}
.sub{color:var(--muted);font-size:12.5px;margin-top:4px}
.head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;margin-bottom:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0 20px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .v{font-size:24px;font-weight:700;margin-top:4px}
.kpi .l{color:var(--muted);font-size:12px}
.kpi .v.good{color:var(--good)} .kpi .v.warn{color:var(--warn)} .kpi .v.bad{color:var(--bad)} .kpi .v.acc{color:var(--accent)}
.tabs{display:flex;gap:8px;margin:6px 0 16px}
.tab{padding:8px 20px;border-radius:20px;border:1px solid var(--line);background:var(--panel);color:var(--muted);cursor:pointer;font-size:14px}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px}
select{background:var(--panel2);color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:13.5px}
.chip{padding:6px 14px;border-radius:16px;border:1px solid var(--line);background:var(--panel);cursor:pointer;font-size:13px;color:var(--muted)}
.chip.on{color:#fff;border-color:transparent}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:2fr 1fr}
@media(max-width:980px){.g2,.g3{grid-template-columns:1fr}}
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
.note{margin-top:22px;color:var(--muted);font-size:12px;line-height:1.8;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.hide{display:none}
</style>
</head>
<body>
<div class="head">
  <div>
    <h1>微信群服务响应 KPI 看板</h1>
    <div class="sub" id="range"></div>
  </div>
  <div class="sub" id="gen"></div>
</div>

<div class="kpis" id="kpis"></div>

<div class="tabs">
  <div class="tab on" data-v="month">月维度</div>
  <div class="tab" data-v="day">日维度</div>
</div>

<div class="bar">
  <span style="color:var(--muted);font-size:13px">人员：</span>
  <span id="chips"></span>
</div>

<!-- MONTH -->
<div id="v-month">
  <div class="bar"><span style="color:var(--muted);font-size:13px">月份：</span><select id="msel"></select></div>
  <div class="card" style="margin-bottom:14px"><h3>人员月度汇总</h3><div style="overflow-x:auto"><table id="mtable"></table></div></div>
  <div class="grid g2" style="margin-bottom:14px">
    <div class="card"><h3>每日发言 / 回复趋势</h3><div id="c1" class="chart"></div></div>
    <div class="card"><h3>每日问题响应：已确认解决 vs 跟进中</h3><div id="c2" class="chart"></div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>人均响应问题数 & 解决率</h3><div id="c3" class="chart"></div></div>
    <div class="card"><h3>平均首响时长 & 30分钟及时率</h3><div id="c4" class="chart"></div></div>
  </div>
</div>

<!-- DAY -->
<div id="v-day" class="hide">
  <div class="bar"><span style="color:var(--muted);font-size:13px">日期：</span><select id="dsel"></select></div>
  <div class="pcards" id="pcards"></div>
  <div class="grid g2" style="margin-bottom:14px">
    <div class="card"><h3>当日各人员发言 / 回复问题</h3><div id="d1" class="chart" style="height:260px"></div></div>
    <div class="card"><h3>当日问题解决分布</h3><div id="d2" class="chart" style="height:260px"></div></div>
  </div>
  <div class="card"><h3>当日问题 / 请求明细（含响应与解决状态）</h3><div style="overflow-x:auto"><table id="dtable"></table></div></div>
</div>

<div class="note">
<b>口径说明（启发式 v1）</b><br>
· 数据源：SiverWXbot 群聊记忆 JSON（3 处目录合并去重）+ 桌面截图人工补录的缺失日期消息。<br>
· 「问题/请求」：群内 @ 关注人员、或含求助/疑问关键词（麻烦、辛苦、看下、联不上、进不去、无法、怎么办…）的非关注人员消息。<br>
· 「回复/响应」：关注人员在同一群、8 小时内对该问题的首条回复；首响时长=问题时间→首条回复时间。<br>
· 「已确认解决」：响应后 4 小时内出现解决信号（响应人：已处理/已开通/已修复/推送了/加完了…；或提出人：好了/收到/谢谢/可以了…）。否则记为「跟进中/未确认」。<br>
· 「及时」：首响 ≤ <span id="ot"></span> 分钟。<br>
· 纯致谢/确认消息（好的、谢谢、收到等）不计为问题。图片/文件等无文本消息不参与问题判定。
</div>

<script>
const DATA = __DATA__;
const PALETTE = ["#5470c6","#91cc75","#fac858","#ee6666","#73c0de","#9a60b4","#fc8452","#4f8cff","#3ecf8e","#f0566a"];
const COLORS = {}; DATA.people.forEach((p,i)=>{ COLORS[p] = PALETTE[i % PALETTE.length]; });
const PEOPLE = DATA.people;
let sel = new Set(PEOPLE);
let view = "month";
let curMonth = null, curDay = null;
const charts = {};

document.getElementById('range').textContent =
  '数据区间 ' + DATA.days[0] + ' ~ ' + DATA.days[DATA.days.length-1] + '　·　消息 ' + DATA.total_msgs + ' 条　·　识别问题/请求 ' + DATA.total_issues + ' 个';
document.getElementById('gen').textContent = '生成时间 ' + DATA.generated;
document.getElementById('ot').textContent = DATA.ontime_min;

function pd(p,d){ return DATA.per_pd[p+'|'+d] || {msgs:0,resp:0,resolved:0,unresolved:0,avg_rt:null,ontime:0}; }
function inSel(p){ return sel.has(p); }
function monthOf(d){ return d.slice(0,7); }
function daysIn(m){ return DATA.days.filter(d=>monthOf(d)===m); }
function months(){ return [...new Set(DATA.days.map(monthOf))].sort(); }

function aggPersonMonth(p,m){
  let a={msgs:0,resp:0,resolved:0,unresolved:0,ontime:0,rt:[]};
  daysIn(m).forEach(d=>{ const v=pd(p,d); a.msgs+=v.msgs; a.resp+=v.resp; a.resolved+=v.resolved; a.unresolved+=v.unresolved; a.ontime+=v.ontime; });
  DATA.issues.forEach(it=>{ if(it.responder===p && monthOf(it.date)===m && it.resp_min!=null) a.rt.push(it.resp_min); });
  a.avg_rt = a.rt.length? +(a.rt.reduce((x,y)=>x+y,0)/a.rt.length).toFixed(1) : null;
  a.ontimeRate = a.resp? Math.round(a.ontime/a.resp*100) : null;
  a.solveRate = a.resp? Math.round(a.resolved/a.resp*100) : null;
  return a;
}
function aggPersonDay(p,d){ return pd(p,d); }
function issuesOfDay(d){ return DATA.issues.filter(i=>i.date===d); }
function issuesOfMonth(m){ return DATA.issues.filter(i=>monthOf(i.date)===m); }

function kpisGlobal(){
  let msgs=0,resp=0,res=0,unres=0,ontime=0,rt=[];
  DATA.days.forEach(d=>PEOPLE.forEach(p=>{ if(!inSel(p))return; const v=pd(p,d);
    msgs+=v.msgs; resp+=v.resp; res+=v.resolved; unres+=v.unresolved; ontime+=v.ontime; }));
  DATA.issues.forEach(i=>{ if(i.responder&&inSel(i.responder)&&i.resp_min!=null) rt.push(i.resp_min); });
  const iss = DATA.issues.filter(i=>i.responder&&inSel(i.responder)).length;
  return {msgs,resp:iss,res,unres,
    rate: iss? Math.round(res/iss*100):0,
    avg: rt.length? (rt.reduce((a,b)=>a+b,0)/rt.length).toFixed(1):'-',
    ontime: rt.length? Math.round(rt.filter(x=>x<=DATA.ontime_min).length/rt.length*100):0};
}
function renderKpis(){
  const k=kpisGlobal();
  document.getElementById('kpis').innerHTML = `
   <div class="kpi"><div class="l">关注人员发言</div><div class="v acc">${k.msgs}</div></div>
   <div class="kpi"><div class="l">识别问题/请求</div><div class="v">${k.resp}</div></div>
   <div class="kpi"><div class="l">已确认解决</div><div class="v good">${k.res}</div></div>
   <div class="kpi"><div class="l">跟进中/未确认</div><div class="v bad">${k.unres}</div></div>
   <div class="kpi"><div class="l">确认解决率</div><div class="v ${k.rate>=50?'good':(k.rate>=25?'warn':'bad')}">${k.rate}%</div></div>
   <div class="kpi"><div class="l">平均首响(分钟)</div><div class="v">${k.avg}</div></div>
   <div class="kpi"><div class="l">${DATA.ontime_min}分钟及时率</div><div class="v ${k.ontime>=70?'good':'warn'}">${k.ontime}%</div></div>`;
}

function buildChips(){
  const c=document.getElementById('chips'); c.innerHTML='';
  PEOPLE.forEach(p=>{
    const el=document.createElement('span'); el.className='chip'+(sel.has(p)?' on':''); el.textContent=p;
    if(sel.has(p)) el.style.background=COLORS[p];
    el.onclick=()=>{ if(sel.has(p)){ if(sel.size>1) sel.delete(p);} else sel.add(p); refresh(); };
    c.appendChild(el);
  });
}

function initSelects(){
  const ms=months(); curMonth=ms[ms.length-1];
  const msel=document.getElementById('msel'); msel.innerHTML=ms.map(m=>`<option>${m}</option>`).join(''); msel.value=curMonth;
  msel.onchange=()=>{curMonth=msel.value; renderMonth();};
  const ds=document.getElementById('dsel'); ds.innerHTML=DATA.days.slice().reverse().map(d=>`<option>${d}</option>`).join('');
  curDay=DATA.days[DATA.days.length-1]; ds.value=curDay;
  ds.onchange=()=>{curDay=ds.value; renderDay();};
}

function mk(id){ if(charts[id]) charts[id].dispose(); charts[id]=echarts.init(document.getElementById(id)); return charts[id]; }
const baseGrid={left:44,right:20,top:36,bottom:30};
const axis={axisLine:{lineStyle:{color:'#3a4763'}},axisLabel:{color:'#8b96ad'},splitLine:{lineStyle:{color:'#232d44'}}};

function renderMonth(){
  const m=curMonth, ds=daysIn(m);
  // table
  let rows='';
  PEOPLE.filter(inSel).forEach(p=>{
    const a=aggPersonMonth(p,m);
    rows+=`<tr><td><span style="color:${COLORS[p]};font-weight:600">${p}</span></td><td>${a.msgs}</td><td>${a.resp}</td>
      <td><span class="pill res">${a.resolved}</span></td><td><span class="pill unres">${a.unresolved}</span></td>
      <td>${a.solveRate==null?'-':a.solveRate+'%'}</td><td>${a.avg_rt==null?'-':a.avg_rt}</td>
      <td>${a.ontimeRate==null?'-':a.ontimeRate+'%'}</td></tr>`;
  });
  document.getElementById('mtable').innerHTML =
    `<thead><tr><th>人员</th><th>发言数</th><th>响应问题数</th><th>已确认解决</th><th>跟进中</th><th>解决率</th><th>平均首响(分)</th><th>及时率</th></tr></thead><tbody>${rows}</tbody>`;

  // c1 daily msgs per person
  mk('c1').setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
    xAxis:{type:'category',data:ds.map(d=>d.slice(5)),...axis},yAxis:{type:'value',...axis},
    series:PEOPLE.filter(inSel).map(p=>({name:p,type:'line',smooth:true,symbolSize:5,
      data:ds.map(d=>pd(p,d).msgs),lineStyle:{width:2},itemStyle:{color:COLORS[p]}}))});

  // c2 daily resolved vs unresolved (selected)
  const resS=ds.map(d=>PEOPLE.filter(inSel).reduce((s,p)=>s+pd(p,d).resolved,0));
  const unS=ds.map(d=>PEOPLE.filter(inSel).reduce((s,p)=>s+pd(p,d).unresolved,0));
  mk('c2').setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
    xAxis:{type:'category',data:ds.map(d=>d.slice(5)),...axis},yAxis:{type:'value',...axis},
    series:[{name:'已确认解决',type:'bar',stack:'a',data:resS,itemStyle:{color:'#3ecf8e'}},
            {name:'跟进中/未确认',type:'bar',stack:'a',data:unS,itemStyle:{color:'#f0566a'}}]});

  // c3 per person resp + solve rate
  const ps=PEOPLE.filter(inSel);
  mk('c3').setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:{...baseGrid,right:44},
    xAxis:{type:'category',data:ps,...axis},yAxis:[{type:'value',...axis},{type:'value',max:100,...axis,axisLabel:{color:'#8b96ad',formatter:'{value}%'}}],
    series:[{name:'响应问题数',type:'bar',data:ps.map(p=>aggPersonMonth(p,m).resp),itemStyle:{color:'#4f8cff'},barWidth:26},
            {name:'解决率',type:'line',yAxisIndex:1,data:ps.map(p=>aggPersonMonth(p,m).solveRate||0),itemStyle:{color:'#fac858'}}]});

  // c4 avg rt + ontime
  mk('c4').setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:{...baseGrid,right:44},
    xAxis:{type:'category',data:ps,...axis},yAxis:[{type:'value',...axis},{type:'value',max:100,...axis,axisLabel:{color:'#8b96ad',formatter:'{value}%'}}],
    series:[{name:'平均首响(分)',type:'bar',data:ps.map(p=>aggPersonMonth(p,m).avg_rt||0),itemStyle:{color:'#73c0de'},barWidth:26},
            {name:'及时率',type:'line',yAxisIndex:1,data:ps.map(p=>aggPersonMonth(p,m).ontimeRate||0),itemStyle:{color:'#3ecf8e'}}]});
}

function renderDay(){
  const d=curDay;
  let cards='';
  PEOPLE.filter(inSel).forEach(p=>{
    const v=pd(p,d);
    const rate=v.resp?Math.round(v.resolved/v.resp*100):null;
    cards+=`<div class="pcard" style="border-left-color:${COLORS[p]}">
      <div class="nm" style="color:${COLORS[p]}">${p}</div>
      <div class="row"><span>发言</span><b>${v.msgs}</b></div>
      <div class="row"><span>响应问题</span><b>${v.resp}</b></div>
      <div class="row"><span>已确认解决</span><b style="color:var(--good)">${v.resolved}</b></div>
      <div class="row"><span>跟进中</span><b style="color:var(--bad)">${v.unresolved}</b></div>
      <div class="row"><span>平均首响</span><b>${v.avg_rt==null?'-':v.avg_rt+'分'}</b></div>
      <div class="row"><span>解决率</span><b>${rate==null?'-':rate+'%'}</b></div></div>`;
  });
  document.getElementById('pcards').innerHTML=cards;

  const ps=PEOPLE.filter(inSel);
  mk('d1').setOption({tooltip:{trigger:'axis'},legend:{textStyle:{color:'#aab4c8'},top:0},grid:baseGrid,
    xAxis:{type:'category',data:ps,...axis},yAxis:{type:'value',...axis},
    series:[{name:'发言',type:'bar',data:ps.map(p=>pd(p,d).msgs),itemStyle:{color:'#4f8cff'}},
            {name:'响应问题',type:'bar',data:ps.map(p=>pd(p,d).resp),itemStyle:{color:'#91cc75'}}]});

  const res=ps.reduce((s,p)=>s+pd(p,d).resolved,0), un=ps.reduce((s,p)=>s+pd(p,d).unresolved,0);
  mk('d2').setOption({tooltip:{trigger:'item'},series:[{type:'pie',radius:['45%','70%'],
    data:[{name:'已确认解决',value:res,itemStyle:{color:'#3ecf8e'}},{name:'跟进中/未确认',value:un,itemStyle:{color:'#f0566a'}}],
    label:{color:'#aab4c8'}}]});

  const iss=issuesOfDay(d).filter(i=>i.responder&&inSel(i.responder));
  let rows='';
  iss.forEach(i=>{
    const st=i.resolved?'<span class="pill res">已确认解决</span>':'<span class="pill wait">跟进中/未确认</span>';
    rows+=`<tr><td>${i.ts.slice(11,16)}</td><td>${i.group}</td><td>${i.author}</td><td class="msg">${i.text.replace(/</g,'&lt;')}</td>
      <td><span style="color:${COLORS[i.responder]}">${i.responder}</span></td>
      <td>${i.resp_min==null?'-':i.resp_min}</td><td>${st}</td></tr>`;
  });
  document.getElementById('dtable').innerHTML = iss.length?
    `<thead><tr><th>时间</th><th>群</th><th>提出人</th><th>问题/请求</th><th>响应人</th><th>首响(分)</th><th>状态</th></tr></thead><tbody>${rows}</tbody>`
    : `<tbody><tr><td style="color:var(--muted)">当日所选人员无识别到的问题/请求</td></tr></tbody>`;
}

function refresh(){
  buildChips(); renderKpis();
  if(view==='month') renderMonth(); else renderDay();
}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on')); t.classList.add('on');
  view=t.dataset.v;
  document.getElementById('v-month').classList.toggle('hide',view!=='month');
  document.getElementById('v-day').classList.toggle('hide',view!=='day');
  refresh();
});
window.addEventListener('resize',()=>Object.values(charts).forEach(c=>c.resize()));

if(typeof echarts==='undefined'){ document.body.insertAdjacentHTML('afterbegin','<div style="color:#f0566a;padding:12px">ECharts 加载失败，请检查网络（图表依赖 CDN）。</div>'); }
initSelects(); refresh();
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
