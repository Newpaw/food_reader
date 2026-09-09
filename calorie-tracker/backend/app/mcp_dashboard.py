from __future__ import annotations

from typing import Any

MCP_APP_DASHBOARD_URI = "ui://foodreader/health-dashboard.html"
OPENAI_DASHBOARD_URI = "ui://foodreader/health-dashboard-openai.html"
MCP_APP_MIME = "text/html;profile=mcp-app"
OPENAI_APP_MIME = "text/html+skybridge"

# The widget is intentionally self-contained: no CDN, fetch(), fonts, or external
# scripts. That keeps it compatible with strict MCP App sandboxes and Cloudflare.
DASHBOARD_HTML = r"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Food Reader</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--surface:#f6f7f6;--surface2:#eef2ef;--text:#17201b;--muted:#657169;--line:#d8dfda;--accent:#1f7a52;--accent2:#6ca889;--warn:#a66500}
@media(prefers-color-scheme:dark){:root{--bg:#171a18;--surface:#202522;--surface2:#29302c;--text:#f0f4f1;--muted:#a5b0a9;--line:#39423c;--accent:#68c99a;--accent2:#4f9e78;--warn:#f4bb55}}
*{box-sizing:border-box}body{margin:0;background:transparent;color:var(--text);font:14px/1.4 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.app{max-width:860px;margin:auto;padding:14px}.card{background:var(--bg);border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:0 8px 30px rgba(0,0,0,.04)}
.header{display:flex;gap:14px;align-items:flex-start;justify-content:space-between;margin-bottom:16px}.title{font-size:20px;font-weight:750;letter-spacing:-.02em}.subtitle{color:var(--muted);margin-top:3px}.badge{white-space:nowrap;padding:6px 10px;background:var(--surface2);border-radius:999px;color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-bottom:16px}.kpi{padding:11px;background:var(--surface);border-radius:12px;min-width:0}.kpi-label{color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kpi-value{font-size:21px;font-weight:750;margin-top:4px;white-space:nowrap}.kpi-unit{font-size:11px;font-weight:500;color:var(--muted);margin-left:2px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}.tab{appearance:none;border:0;background:var(--surface);color:var(--muted);padding:7px 10px;border-radius:999px;font:inherit;cursor:pointer}.tab.active{background:var(--text);color:var(--bg)}.chart-wrap{height:230px;background:linear-gradient(180deg,var(--surface),transparent);border-radius:14px;padding:8px}.chart{width:100%;height:100%;overflow:visible}.grid{stroke:var(--line);stroke-width:1}.axis{fill:var(--muted);font-size:10px}.plot{fill:none;stroke:var(--accent);stroke-width:3;stroke-linejoin:round;stroke-linecap:round}.plot2{fill:none;stroke:var(--accent2);stroke-width:2;stroke-dasharray:5 4}.dot{fill:var(--accent);stroke:var(--bg);stroke-width:2}.bar{fill:var(--accent);opacity:.82}.empty{height:100%;display:flex;align-items:center;justify-content:center;color:var(--muted)}
.footer{display:grid;grid-template-columns:1.25fr 1fr;gap:12px;margin-top:14px}.panel{background:var(--surface);border-radius:12px;padding:12px}.panel-title{font-weight:700;margin-bottom:6px}.insight{color:var(--muted);font-size:12px;margin-top:5px}.legend{display:flex;gap:12px;color:var(--muted);font-size:11px;margin-top:8px}.legend i{display:inline-block;width:10px;height:3px;border-radius:3px;background:var(--accent);vertical-align:middle;margin-right:4px}.legend i.alt{background:var(--accent2)}
@media(max-width:700px){.kpis{grid-template-columns:repeat(3,1fr)}.footer{grid-template-columns:1fr}.card{padding:14px}}@media(max-width:420px){.kpis{grid-template-columns:repeat(2,1fr)}.app{padding:8px}.header{display:block}.badge{display:inline-block;margin-top:8px}}
</style>
</head>
<body>
<div class="app"><section class="card">
  <div class="header"><div><div class="title" id="title">Food Reader</div><div class="subtitle" id="subtitle">Načítám data…</div></div><div class="badge" id="badge">MCP App</div></div>
  <div class="kpis" id="kpis"></div>
  <div class="tabs" id="tabs"></div>
  <div class="chart-wrap"><svg class="chart" id="chart" viewBox="0 0 760 220" preserveAspectRatio="none"></svg><div class="empty" id="empty" hidden>Pro zvolené období nejsou data.</div></div>
  <div class="legend" id="legend"></div>
  <div class="footer"><div class="panel"><div class="panel-title">Souhrn</div><div id="summary" class="insight">—</div></div><div class="panel"><div class="panel-title">Postřehy</div><div id="insights"></div></div></div>
</section></div>
<script>
(() => {
  const $ = (id) => document.getElementById(id);
  let state = null;
  let activeMetric = null;
  const esc = (v) => String(v ?? "").replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const num = (v, digits=0) => (v === null || v === undefined || Number.isNaN(Number(v))) ? "—" : Number(v).toLocaleString('cs-CZ',{maximumFractionDigits:digits});
  const dateLabel = (s) => { if(!s) return ''; const d=new Date(String(s).length===10?s+'T12:00:00':s); return Number.isNaN(d.getTime())?String(s):d.toLocaleDateString('cs-CZ',{day:'numeric',month:'numeric'}); };
  const latest = (arr, getter) => { for(let i=arr.length-1;i>=0;i--){const v=getter(arr[i]); if(v!==null&&v!==undefined)return v;} return null; };

  function normalize(raw){
    const d = raw?.structuredContent ?? raw?.result?.structuredContent ?? raw?.toolOutput ?? raw;
    if(!d || typeof d !== 'object') return null;
    if(Array.isArray(d.days)){
      const rows=d.days.map(x=>({day:x.day,calories:x.nutrition?.calories??0,protein:x.nutrition?.protein_g??0,readiness:x.oura?.readiness_score??null,sleep:x.oura?.sleep_score??null,activity:x.oura?.activity_score??null,steps:x.oura?.steps??null}));
      return {kind:'health',rows,targets:d.targets??{},summary:d.summary??{},insights:d.insights??[],from:d.from,to:d.to,timezone:d.timezone};
    }
    if(Array.isArray(d.rows)){
      const first=d.rows[0]||{};
      if('day' in first || 'readiness_score' in first) return {kind:'oura',rows:d.rows.slice().reverse().map(x=>({day:x.day,readiness:x.readiness_score,sleep:x.sleep_score,activity:x.activity_score,steps:x.steps,calories:x.total_calories})),summary:{},insights:[]};
      if('measured_at' in first || 'weight_kg' in first) return {kind:'withings',rows:d.rows.slice().reverse().map(x=>({day:x.measured_at,weight:x.weight_kg,fat:x.fat_ratio,muscle:x.muscle_mass_kg})),summary:{},insights:[]};
      if('consumed_at' in first || 'meal_type' in first) return normalizeMeals(d.rows);
    }
    return null;
  }

  function normalizeMeals(rows){
    const by={};
    rows.forEach(x=>{const key=String(x.consumed_at||'').slice(0,10)||'unknown';const r=by[key]||(by[key]={day:key,calories:0,protein:0,count:0});r.calories+=Number(x.calories||0);r.protein+=Number(x.protein_g||0);r.count++;});
    return {kind:'meals',rows:Object.values(by).sort((a,b)=>String(a.day).localeCompare(String(b.day))),summary:{meal_count:rows.length},insights:[]};
  }

  const configs={
    health:[['calories','Kalorie','kcal','bar'],['readiness','Readiness','b','line'],['sleep','Spánek','b','line'],['protein','Protein','g','bar']],
    oura:[['readiness','Readiness','b','line'],['sleep','Spánek','b','line'],['activity','Aktivita','b','line'],['steps','Kroky','','line']],
    withings:[['weight','Hmotnost','kg','line'],['fat','Tuk','%','line'],['muscle','Svaly','kg','line']],
    meals:[['calories','Kalorie','kcal','bar'],['protein','Protein','g','bar']]
  };

  function kpi(label,value,unit=''){return `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}${unit?`<span class="kpi-unit">${esc(unit)}</span>`:''}</div></div>`;}

  function renderKpis(s){
    const r=s.rows||[]; let html='';
    if(s.kind==='health'||s.kind==='oura'){
      html+=kpi('Readiness',num(latest(r,x=>x.readiness)),'b');html+=kpi('Spánek',num(latest(r,x=>x.sleep)),'b');html+=kpi('Aktivita',num(latest(r,x=>x.activity)),'b');html+=kpi('Kroky',num(latest(r,x=>x.steps)),'');
    }
    if(s.kind==='health'){html+=kpi('Dnešní kcal',num(r.at(-1)?.calories),'kcal');html+=kpi('Hmotnost',num(s.summary?.latest_weight_kg,1),'kg');}
    if(s.kind==='withings'){html+=kpi('Hmotnost',num(latest(r,x=>x.weight),1),'kg');html+=kpi('Tuk',num(latest(r,x=>x.fat),1),'%');html+=kpi('Svaly',num(latest(r,x=>x.muscle),1),'kg');}
    if(s.kind==='meals'){html+=kpi('Záznamy',num(s.summary?.meal_count),'');html+=kpi('Poslední den',num(r.at(-1)?.calories),'kcal');html+=kpi('Protein',num(r.at(-1)?.protein),'g');}
    $('kpis').innerHTML=html||kpi('Data','—','');
  }

  function renderTabs(s){
    const cfg=configs[s.kind]||[]; if(!activeMetric||!cfg.some(x=>x[0]===activeMetric)) activeMetric=cfg[0]?.[0];
    $('tabs').innerHTML=cfg.map(([key,label])=>`<button class="tab ${key===activeMetric?'active':''}" data-key="${key}">${esc(label)}</button>`).join('');
    [...$('tabs').querySelectorAll('.tab')].forEach(b=>b.onclick=()=>{activeMetric=b.dataset.key;renderTabs(s);renderChart(s);});
  }

  function metricCfg(s){return (configs[s.kind]||[]).find(x=>x[0]===activeMetric)||['','','','line'];}
  function renderChart(s){
    const svg=$('chart'), empty=$('empty'); const [key,label,unit,type]=metricCfg(s); const rows=(s.rows||[]).filter(x=>x[key]!==null&&x[key]!==undefined);
    if(!rows.length){svg.innerHTML='';svg.hidden=true;empty.hidden=false;$('legend').innerHTML='';return;} svg.hidden=false;empty.hidden=true;
    const W=760,H=220,p={l:38,r:12,t:12,b:28}; const vals=rows.map(x=>Number(x[key])); let min=Math.min(...vals),max=Math.max(...vals); if(key==='readiness'||key==='sleep'||key==='activity'){min=0;max=100;} else if(min===max){min=Math.max(0,min-1);max=max+1;} else {const pad=(max-min)*.12;min=Math.max(0,min-pad);max+=pad;}
    const x=i=>p.l+(rows.length===1?0.5:(i/(rows.length-1)))*(W-p.l-p.r); const y=v=>p.t+(max-v)/(max-min||1)*(H-p.t-p.b);
    let out=''; for(let i=0;i<5;i++){const yy=p.t+i*(H-p.t-p.b)/4;const val=max-i*(max-min)/4;out+=`<line class="grid" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text class="axis" x="2" y="${yy+4}">${Math.round(val)}</text>`;}
    const step=Math.max(1,Math.ceil(rows.length/5)); rows.forEach((r,i)=>{if(i%step===0||i===rows.length-1)out+=`<text class="axis" text-anchor="middle" x="${x(i)}" y="${H-5}">${esc(dateLabel(r.day))}</text>`;});
    if(type==='bar'){
      const bw=Math.max(3,Math.min(34,(W-p.l-p.r)/Math.max(rows.length,1)*.62)); rows.forEach((r,i)=>{const yy=y(Number(r[key]));out+=`<rect class="bar" x="${x(i)-bw/2}" y="${yy}" width="${bw}" height="${Math.max(1,H-p.b-yy)}" rx="3"><title>${esc(dateLabel(r.day))}: ${esc(num(r[key],1))} ${esc(unit)}</title></rect>`;});
    }else{
      const pts=rows.map((r,i)=>`${x(i)},${y(Number(r[key]))}`).join(' ');out+=`<polyline class="plot" points="${pts}"/>`;rows.forEach((r,i)=>{out+=`<circle class="dot" cx="${x(i)}" cy="${y(Number(r[key]))}" r="4"><title>${esc(dateLabel(r.day))}: ${esc(num(r[key],1))} ${esc(unit)}</title></circle>`;});
    }
    if(s.kind==='health'&&(key==='calories'||key==='protein')){const target=key==='calories'?s.targets?.calories:s.targets?.protein_g;if(target!=null&&target>=min&&target<=max){const yy=y(Number(target));out+=`<line class="plot2" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/>`;$('legend').innerHTML=`<span><i></i>${esc(label)}</span><span><i class="alt"></i>Cíl ${esc(num(target))} ${esc(unit)}</span>`;}else $('legend').innerHTML=`<span><i></i>${esc(label)}</span>`;}else $('legend').innerHTML=`<span><i></i>${esc(label)}</span>`;
    svg.innerHTML=out;
  }

  function renderText(s){
    const count=s.rows?.length||0; $('title').textContent=s.kind==='oura'?'Oura × Food Reader':s.kind==='withings'?'Withings × Food Reader':s.kind==='meals'?'Výživa × Food Reader':'Food Reader Health';
    $('subtitle').textContent=s.from&&s.to?`${dateLabel(s.from)} – ${dateLabel(s.to)} · ${s.timezone||''}`:`${count} záznamů`;
    $('badge').textContent=s.kind==='health'?`${s.summary?.days_with_oura??0} dnů Oura · ${s.summary?.days_with_food??0} dnů jídla`:'MCP App';
    const avg=s.summary?.average_energy_balance_kcal; const rd=s.summary?.average_readiness; const sl=s.summary?.average_sleep_score; let summary=[]; if(avg!=null)summary.push(`Průměrná bilance ${num(avg)} kcal/den`);if(rd!=null)summary.push(`readiness ${num(rd,1)}`);if(sl!=null)summary.push(`sleep ${num(sl,1)}`); if(!summary.length)summary.push(`${count} datových bodů`);$('summary').textContent=summary.join(' · ');
    const insights=(s.insights||[]).slice(0,3);$('insights').innerHTML=insights.length?insights.map(x=>`<div class="insight"><strong>${esc(x.title||'')}</strong><br>${esc(x.detail||'')}</div>`).join(''):'<div class="insight">Bez dalších postřehů pro toto období.</div>';
  }

  function render(raw){const s=normalize(raw);if(!s)return;state=s;renderKpis(s);renderTabs(s);renderChart(s);renderText(s);}

  // OpenAI Apps compatibility: current ChatGPT hosts expose toolOutput here.
  try{if(window.openai?.toolOutput)render(window.openai.toolOutput);}catch(_){ }
  window.addEventListener('openai:set_globals',()=>{try{if(window.openai?.toolOutput)render(window.openai.toolOutput);}catch(_){ }});

  // Standard MCP Apps: hosts post the originating tool result into the iframe.
  window.addEventListener('message',(event)=>{
    const msg=event.data; const candidate=msg?.result ?? msg?.params?.result ?? msg?.toolOutput;
    if(candidate)render(candidate);
  });
})();
</script>
</body></html>"""


def _merge_app_meta(current: dict[str, Any] | None) -> dict[str, Any]:
    meta = dict(current or {})
    meta["ui"] = {
        "resourceUri": MCP_APP_DASHBOARD_URI,
        "visibility": ["model", "app"],
    }
    # Compatibility with pre-GA MCP Apps hosts.
    meta["ui/resourceUri"] = MCP_APP_DASHBOARD_URI
    # Compatibility with ChatGPT/OpenAI Apps hosts that still read the old keys.
    meta["openai/outputTemplate"] = OPENAI_DASHBOARD_URI
    meta["openai/widgetAccessible"] = True
    meta["openai/visibility"] = "public"
    meta["openai/toolInvocation/invoking"] = "Načítám Food Reader…"
    meta["openai/toolInvocation/invoked"] = "Food Reader připraven"
    return meta


def register_mcp_dashboard(mcp: Any) -> None:
    """Attach one self-contained MCP App UI to the existing read tools.

    This deliberately does not add another model-visible tool. The dashboard is
    the presentation layer for existing structured results, so clients without
    MCP Apps support continue to receive exactly the same tool data as before.
    """

    if getattr(mcp, "_food_reader_dashboard_registered", False):
        return

    @mcp.resource(
        MCP_APP_DASHBOARD_URI,
        name="Food Reader health dashboard",
        title="Food Reader health dashboard",
        description="Interactive Food Reader/Oura/Withings/nutrition dashboard for MCP Apps hosts.",
        mime_type=MCP_APP_MIME,
    )
    def _health_dashboard_resource() -> str:
        return DASHBOARD_HTML

    @mcp.resource(
        OPENAI_DASHBOARD_URI,
        name="Food Reader health dashboard (OpenAI compatibility)",
        title="Food Reader health dashboard",
        description="Compatibility resource for ChatGPT hosts using the legacy OpenAI Apps MIME type.",
        mime_type=OPENAI_APP_MIME,
    )
    def _health_dashboard_openai_resource() -> str:
        return DASHBOARD_HTML

    # FastMCP v1 exposes metadata through the registered Tool model. Patch only
    # presentation metadata and preserve the existing OAuth securitySchemes.
    tool_manager = getattr(mcp, "_tool_manager", None)
    if tool_manager is None:
        raise RuntimeError("FastMCP tool manager is unavailable")

    for tool_name in (
        "get_health_summary",
        "get_oura_daily",
        "get_withings_measurements",
        "get_meals",
    ):
        tool = tool_manager.get_tool(tool_name)
        if tool is None:
            raise RuntimeError(f"Cannot attach dashboard: MCP tool {tool_name!r} is missing")
        tool.meta = _merge_app_meta(tool.meta)

    setattr(mcp, "_food_reader_dashboard_registered", True)
