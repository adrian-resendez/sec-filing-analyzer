from __future__ import annotations

from flask import Blueprint, Response

bp = Blueprint("research", __name__)


@bp.get("/")
def research_workspace() -> Response:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Filing Intelligence</title>
  <style>
    :root{--midnight:#0B1324;--slate:#15233C;--paper:#F6F4EE;--ink:#112033;--steel:#5F7086;--line:#D5DEEA;--cobalt:#2D5BFF;--aqua:#67D6FF;--emerald:#0C8A6A;--amber:#D38A1F;--rose:#B94A5A;--shadow:0 22px 55px rgba(17,32,51,.10)}
    *{box-sizing:border-box}body{margin:0;font-family:"Avenir Next","Trebuchet MS",sans-serif;color:var(--ink);background:radial-gradient(circle at top left,rgba(103,214,255,.2),transparent 30%),radial-gradient(circle at top right,rgba(45,91,255,.14),transparent 24%),linear-gradient(180deg,#EDF4FF 0,#F6F1E8 100%)}a{color:var(--cobalt);text-decoration:none}
    .shell{width:min(1440px,calc(100% - 24px));margin:0 auto;padding:20px 0 28px}.panel{background:rgba(246,244,238,.94);border:1px solid rgba(17,32,51,.08);border-radius:28px;box-shadow:var(--shadow)}.serif{font-family:"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,serif}.mono{font-family:"Cascadia Code","SFMono-Regular",Consolas,monospace}
    .hero{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;padding:22px;margin-bottom:18px;color:#fff;background:radial-gradient(circle at 18% 18%,rgba(103,214,255,.22),transparent 24%),radial-gradient(circle at 84% 14%,rgba(45,91,255,.24),transparent 22%),linear-gradient(135deg,rgba(11,19,36,.98),rgba(21,35,60,.96))}.eyebrow{display:inline-flex;gap:8px;align-items:center;padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.08);color:#CFE9FF;text-transform:uppercase;letter-spacing:.08em;font-size:.74rem}.eyebrow:before{content:"";width:8px;height:8px;border-radius:50%;background:var(--aqua);box-shadow:0 0 16px rgba(103,214,255,.85)}
    h1{margin:14px 0 10px;font-size:clamp(2.5rem,4.8vw,4.8rem);line-height:.95;letter-spacing:-.05em;max-width:10ch}.hero p{margin:0;max-width:46rem;color:rgba(229,241,255,.82);line-height:1.6}.hero-stats{display:grid;gap:12px}.hero-stat{padding:16px 18px;border-radius:20px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.10)}.hero-stat .k{color:rgba(213,232,255,.72);text-transform:uppercase;letter-spacing:.08em;font-size:.72rem}.hero-stat .v{margin-top:8px;font-size:1.9rem;line-height:1}.hero-stat .f{margin-top:7px;color:rgba(229,241,255,.76);font-size:.92rem}
    .layout{display:grid;grid-template-columns:340px 1fr;gap:18px;align-items:start}.rail{position:sticky;top:16px;padding:18px;background:linear-gradient(160deg,rgba(15,29,54,.99),rgba(21,35,60,.96));color:#fff;border:1px solid rgba(255,255,255,.08);border-radius:28px;box-shadow:var(--shadow);max-height:calc(100vh - 32px);overflow:hidden}.rail h2,.detail h2,.detail h3{margin:0}.rail p{margin:8px 0 0;color:rgba(229,241,255,.72);line-height:1.5}.search{width:100%;margin:16px 0 12px;padding:14px 16px;border-radius:18px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.08);color:#fff;font:inherit}.search::placeholder{color:rgba(229,241,255,.52)}.toggle{display:flex;gap:10px;align-items:center;color:rgba(229,241,255,.78);font-size:.9rem;margin-bottom:14px}.list{display:grid;gap:10px;overflow:auto;max-height:calc(100vh - 230px);padding-right:4px}
    .company{width:100%;text-align:left;padding:14px 16px;border-radius:20px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.06);color:#fff;cursor:pointer}.company:hover,.company.active{background:rgba(255,255,255,.10);border-color:rgba(103,214,255,.42)}.company-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.ticker{font-size:1rem;font-weight:700;letter-spacing:.03em}.name{margin-top:3px;color:rgba(229,241,255,.82);font-size:.92rem;line-height:1.35}.meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
    .badge{display:inline-flex;gap:8px;align-items:center;padding:6px 10px;border-radius:999px;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}.badge:before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}.ok{background:rgba(12,138,106,.16);color:var(--emerald)}.warn{background:rgba(211,138,31,.16);color:#9A5D00}.bad{background:rgba(185,74,90,.16);color:var(--rose)}.muted{background:rgba(255,255,255,.10);color:rgba(229,241,255,.72)}
    .detail{display:grid;gap:18px}.head{padding:22px}.head-top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap}.head h2{font-size:clamp(2rem,3.6vw,3.3rem);line-height:.97}.subline{margin-top:8px;color:var(--steel);line-height:1.6;max-width:52rem}.status{display:inline-flex;gap:8px;align-items:center;padding:8px 12px;border-radius:999px;background:rgba(45,91,255,.10);color:var(--cobalt);font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em}.status:before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor}
    .market{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{padding:16px;border-radius:20px;background:rgba(255,255,255,.72);border:1px solid rgba(17,32,51,.06)}.card .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--steel)}.card .v{margin-top:8px;font-size:1.55rem;line-height:1.02}.card .f{margin-top:7px;color:var(--steel);font-size:.9rem}
    .chart{padding:16px;border-radius:22px;background:linear-gradient(180deg,rgba(21,35,60,.98),rgba(11,19,36,.96));color:#fff;min-height:270px;display:grid;gap:12px}.chart p{margin:6px 0 0;color:rgba(229,241,255,.72);line-height:1.5}.chart-svg{width:100%;height:180px;display:block}.chart-meta{display:flex;justify-content:space-between;gap:12px;color:rgba(229,241,255,.72);font-size:.9rem}
    .section{padding:20px}.section p{margin:8px 0 0;color:var(--steel);line-height:1.55}.narrative{display:grid;gap:14px;margin-top:14px}.story{padding:18px;border-radius:22px;background:rgba(255,255,255,.76);border:1px solid rgba(17,32,51,.07)}.story h3{margin-bottom:10px}.story p{margin:0 0 12px;line-height:1.7;color:var(--ink)}.citations{display:grid;gap:10px;margin-top:8px}.citation{padding:12px 14px;border-radius:18px;background:var(--paper-2);border:1px solid rgba(17,32,51,.07)}.citation .top{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}.citation .label{font-size:.88rem;font-weight:700}.citation .section-name{color:var(--cobalt);font-size:.84rem}.citation .excerpt{margin-top:8px;color:var(--steel);line-height:1.6;font-size:.93rem}
    .filings{display:grid;gap:14px;margin-top:14px}.filing{padding:18px;border-radius:22px;background:rgba(255,255,255,.76);border:1px solid rgba(17,32,51,.07);display:grid;gap:14px}.filing-top{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap}.filing-top h3{font-size:1.25rem}.meta-line{margin-top:6px;color:var(--steel);line-height:1.5}.filing-body{display:grid;grid-template-columns:1.05fr .95fr;gap:16px}.copy p{margin:0 0 12px;line-height:1.7}.list-block{display:grid;gap:10px}.list-block h4{margin:0;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--steel)}.list-block ul{margin:0;padding-left:18px;line-height:1.6}
    details{border-top:1px solid rgba(17,32,51,.08);padding-top:12px}summary{cursor:pointer;color:var(--steel);font-weight:700;list-style:none}summary::-webkit-details-marker{display:none}.source-links{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.empty{padding:18px;border-radius:20px;background:rgba(255,255,255,.70);border:1px dashed rgba(17,32,51,.16);color:var(--steel);line-height:1.6}.pos{color:var(--emerald)}.neg{color:var(--rose)}.neu{color:var(--steel)}
    @media (max-width:1180px){.hero,.layout,.market,.filing-body{grid-template-columns:1fr}.rail{position:static;max-height:none}.list{max-height:360px}.cards{grid-template-columns:repeat(2,1fr)}}@media (max-width:760px){.shell{width:min(100% - 16px,1440px)}.cards{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero panel">
      <div>
        <div class="eyebrow">Local Research File</div>
        <h1 class="serif">Filing Intelligence</h1>
        <p>Search the local S&amp;P company list, read saved quarterly analysis with citations, and keep source filing documents available without letting them dominate the page.</p>
      </div>
      <div class="hero-stats">
        <div class="hero-stat"><div class="k">Stored Universe</div><div class="v serif" id="stat-companies">-</div><div class="f">Active companies in PostgreSQL</div></div>
        <div class="hero-stat"><div class="k">Quarterly Coverage</div><div class="v serif" id="stat-filings">-</div><div class="f">Local filings saved for exploration</div></div>
        <div class="hero-stat"><div class="k">Completed Analysis</div><div class="v serif" id="stat-analyzed">-</div><div class="f">AI summaries ready to review</div></div>
      </div>
    </section>
    <section class="layout">
      <aside class="rail">
        <h2 class="serif">Company List</h2>
        <p>Coverage-first browsing with fast search over the local active universe.</p>
        <input id="search" class="search" type="search" placeholder="Search ticker, company, sector, or industry"/>
        <label class="toggle"><input id="with-filings" type="checkbox"/> Only show companies with stored filings</label>
        <div id="company-list" class="list"></div>
      </aside>
      <main class="detail">
        <section class="panel head">
          <div class="head-top">
            <div>
              <div class="eyebrow">Selected Company</div>
              <h2 id="company-title" class="serif">Loading...</h2>
              <div id="company-subline" class="subline">Pulling local coverage, market context, and filing summaries.</div>
            </div>
            <div id="coverage-chip" class="status">Loading</div>
          </div>
          <div class="market">
            <section class="panel section">
              <div class="cards">
                <article class="card"><div class="k">Price Per Share</div><div id="m-price" class="v serif">-</div><div id="m-change" class="f">Current session context</div></article>
                <article class="card"><div class="k">6-Month Return</div><div id="m-return" class="v serif">-</div><div id="m-range" class="f">Price range over the last six months</div></article>
                <article class="card"><div class="k">Market Cap</div><div id="m-cap" class="v serif">-</div><div id="m-shares" class="f">Shares outstanding when available</div></article>
                <article class="card"><div class="k">Coverage</div><div id="m-coverage" class="v serif">-</div><div id="m-industry" class="f">Local filing archive coverage</div></article>
              </div>
              <div id="market-note" class="empty" style="margin-top:14px">Select a company to load Polygon market context.</div>
            </section>
            <section class="chart">
              <div>
                <h3 class="serif">6-Month Price History</h3>
                <p>Compact daily view for the selected ticker so you can keep market context beside the filing narrative.</p>
              </div>
              <div id="chart-badge" class="status">Waiting</div>
              <svg id="history-chart" class="chart-svg" viewBox="0 0 640 180" preserveAspectRatio="none"></svg>
              <div class="chart-meta"><span id="chart-start">-</span><span id="chart-end">-</span></div>
            </section>
          </div>
        </section>
        <section class="panel section">
          <h2 class="serif">Research Summary</h2>
          <p id="summary-subline">The narrative below is built from filing analysis already saved in PostgreSQL, with citations tied back to the relevant 10-Q and section evidence.</p>
          <div id="summary-sections" class="narrative"></div>
        </section>
        <section class="panel section">
          <h2 class="serif">Quarterly Report Archive</h2>
          <p>Latest filings stay visible, but source document links are tucked into collapsible details so the research narrative stays in front.</p>
          <div id="filing-cards" class="filings"></div>
        </section>
      </main>
    </section>
  </div>
  <script>
    const companyListEl=document.getElementById("company-list"),searchEl=document.getElementById("search"),withFilingsEl=document.getElementById("with-filings");let companies=[],selectedTicker=null;
    const fmtN=v=>new Intl.NumberFormat().format(v??0),fmtC=v=>v===null||v===undefined||v===""?"-":new Intl.NumberFormat("en-US",{notation:"compact",maximumFractionDigits:1}).format(Number(v)),fmtP=v=>v===null||v===undefined||v===""?"-":new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:2}).format(Number(v)),fmtPct=v=>v===null||v===undefined||v===""?"-":`${Number(v).toFixed(2)}%`,fmtDate=v=>{if(!v)return"-";const d=new Date(v);return Number.isNaN(d.getTime())?v:d.toLocaleDateString()};
    function statusClass(status){const s=String(status||"").toLowerCase();if(s.includes("fail"))return"bad";if(s.includes("pending")||s.includes("extract")||s.includes("analy"))return"warn";if(s==="no_filings")return"muted";return"ok"}
    function renderList(){const q=searchEl.value.trim().toLowerCase();const filtered=companies.filter(c=>!(withFilingsEl.checked&&c.filing_count===0)&&(!q||`${c.ticker} ${c.name||""} ${c.sector||""} ${c.industry||""}`.toLowerCase().includes(q)));companyListEl.innerHTML="";if(!filtered.length){companyListEl.innerHTML='<div class="empty">No companies match the current filter.</div>';return}filtered.forEach(c=>{const b=document.createElement("button");b.type="button";b.className=`company ${selectedTicker===c.ticker?"active":""}`;b.innerHTML=`<div class="company-top"><div><div class="ticker mono">${c.ticker}</div><div class="name">${c.name||"Unnamed issuer"}</div></div><span class="badge ${statusClass(c.latest_status)}">${(c.latest_status||"no_filings").replaceAll("_"," ")}</span></div><div class="meta"><span class="badge muted">${c.filing_count} filing${c.filing_count===1?"":"s"}</span><span class="badge muted">${c.analyzed_count} analyzed</span></div>`;b.onclick=()=>loadWorkspace(c.ticker);companyListEl.appendChild(b)})}
    function renderStats(){document.getElementById("stat-companies").textContent=fmtN(companies.length);document.getElementById("stat-filings").textContent=fmtN(companies.reduce((s,c)=>s+c.filing_count,0));document.getElementById("stat-analyzed").textContent=fmtN(companies.reduce((s,c)=>s+c.analyzed_count,0))}
    function lineChart(history){const svg=document.getElementById("history-chart");if(!history||history.length<2){svg.innerHTML="";document.getElementById("chart-start").textContent="No recent history";document.getElementById("chart-end").textContent="";return}const w=640,h=180,p=18,closes=history.map(x=>Number(x.close)).filter(x=>!Number.isNaN(x)),min=Math.min(...closes),max=Math.max(...closes),range=Math.max(max-min,1),step=(w-p*2)/Math.max(history.length-1,1),pts=history.map((point,i)=>({x:p+step*i,y:h-p-((Number(point.close)-min)/range)*(h-p*2)})),line=pts.map((pt,i)=>`${i===0?"M":"L"} ${pt.x.toFixed(2)} ${pt.y.toFixed(2)}`).join(" "),area=`${line} L ${pts[pts.length-1].x.toFixed(2)} ${(h-p).toFixed(2)} L ${pts[0].x.toFixed(2)} ${(h-p).toFixed(2)} Z`;svg.innerHTML=`<defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="rgba(103,214,255,.42)"></stop><stop offset="100%" stop-color="rgba(103,214,255,.02)"></stop></linearGradient></defs><path d="${area}" fill="url(#fill)"></path><path d="${line}" fill="none" stroke="#67D6FF" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>`;document.getElementById("chart-start").textContent=fmtDate(history[0].date);document.getElementById("chart-end").textContent=fmtDate(history[history.length-1].date)}
    function renderMarket(company,market,coverage){document.getElementById("company-title").textContent=company.name||company.ticker;document.getElementById("company-subline").textContent=`${company.ticker}${company.exchange?" | "+company.exchange:""}${company.sector?" | "+company.sector:""}${company.industry?" | "+company.industry:""}`;document.getElementById("coverage-chip").textContent=`${coverage.analyzed_count} analyzed quarter${coverage.analyzed_count===1?"":"s"}`;if(market.error){document.getElementById("m-price").textContent="-";document.getElementById("m-change").textContent=market.error;document.getElementById("m-return").textContent="-";document.getElementById("m-range").textContent="Polygon data unavailable";document.getElementById("m-cap").textContent="-";document.getElementById("m-shares").textContent="-";document.getElementById("m-coverage").textContent=`${coverage.filing_count} filing${coverage.filing_count===1?"":"s"}`;document.getElementById("m-industry").textContent=company.industry||company.sector||"Local coverage only";document.getElementById("market-note").innerHTML=`<div class="empty">${market.error}</div>`;document.getElementById("chart-badge").textContent="No market feed";lineChart([]);return}const cls=Number(market.today_change)>0?"pos":Number(market.today_change)<0?"neg":"neu";document.getElementById("m-price").textContent=fmtP(market.current_price);document.getElementById("m-change").innerHTML=`<span class="${cls}">${fmtP(market.today_change)} | ${fmtPct(market.today_change_percent)}</span>`;document.getElementById("m-return").innerHTML=`<span class="${Number(market.six_month_return)>=0?"pos":"neg"}">${fmtPct(market.six_month_return)}</span>`;document.getElementById("m-range").textContent=`${fmtP(market.six_month_low)} to ${fmtP(market.six_month_high)}`;document.getElementById("m-cap").textContent=fmtC(market.market_cap);document.getElementById("m-shares").textContent=market.shares_outstanding?`${fmtC(market.shares_outstanding)} shares`:"Shares unavailable";document.getElementById("m-coverage").textContent=`${coverage.filing_count} filing${coverage.filing_count===1?"":"s"}`;document.getElementById("m-industry").textContent=company.industry||company.sector||"Local archive coverage";document.getElementById("market-note").innerHTML=`<div class="empty"><strong>Current market context</strong><br/>Previous close: ${fmtP(market.previous_close)}. Session range: ${fmtP(market.low)} to ${fmtP(market.high)}. Volume: ${fmtC(market.volume)}.${market.description?`<br/><br/>${market.description}`:""}</div>`;document.getElementById("chart-badge").textContent=`${company.ticker} market view`;lineChart(market.history||[])}
    function renderSummary(summary){document.getElementById("summary-subline").textContent=summary.subheadline||"Stored narrative coverage.";const root=document.getElementById("summary-sections");root.innerHTML="";const top=document.createElement("article");top.className="story";top.innerHTML=`<h3 class="serif">Topline Read</h3><p>${summary.headline||"No summary available."}</p>`;root.appendChild(top);(summary.sections||[]).forEach(section=>{const card=document.createElement("article");card.className="story";const paragraphs=(section.paragraphs||[]).map(p=>`<p>${p}</p>`).join("");const cites=(section.citations||[]).map(c=>`<div class="citation"><div class="top"><div class="label">${c.label||"Source"}</div><div class="section-name">${c.section_name||""}</div></div>${c.excerpt?`<div class="excerpt">${c.excerpt}</div>`:""}${c.url?`<div class="excerpt"><a href="${c.url}" target="_blank" rel="noreferrer">Open filing source</a></div>`:""}</div>`).join("");card.innerHTML=`<h3 class="serif">${section.title}</h3>${paragraphs}${cites?`<div class="citations">${cites}</div>`:""}`;root.appendChild(card)})}
    function renderFilings(filings){const root=document.getElementById("filing-cards");root.innerHTML="";if(!filings.length){root.innerHTML='<div class="empty">No local filings are stored yet for this company.</div>';return}filings.forEach(f=>{const insight=f.insight,pros=(insight?.investor_pros||[]).slice(0,4).map(x=>`<li>${x}</li>`).join(""),cons=(insight?.investor_cons||[]).slice(0,4).map(x=>`<li>${x}</li>`).join(""),links=(f.source_links||[]).map(x=>`<a href="${x.url}" target="_blank" rel="noreferrer">${x.label}</a>`).join(""),cites=(f.citations||[]).slice(0,3).map(c=>`<div class="citation"><div class="top"><div class="label">${c.label||"Source"}</div><div class="section-name">${c.section_name||""}</div></div>${c.excerpt?`<div class="excerpt">${c.excerpt}</div>`:""}</div>`).join("");const card=document.createElement("article");card.className="filing";card.innerHTML=`<div class="filing-top"><div><h3 class="serif">${f.form_type} filed ${fmtDate(f.filed_at)}</h3><div class="meta-line mono">${f.accession_no}</div></div><span class="badge ${statusClass(f.processing_status)}">${f.processing_status.replaceAll("_"," ")}</span></div><div class="filing-body"><div class="copy"><p>${insight?.executive_summary||"This filing is stored locally, but it does not yet have a completed AI summary."}</p>${cites?`<div class="citations">${cites}</div>`:""}</div><div class="list-block">${insight?`<div><h4>Positive Signals</h4><ul>${pros||"<li>No positive signals extracted yet.</li>"}</ul></div><div><h4>Watch Items</h4><ul>${cons||"<li>No risks extracted yet.</li>"}</ul></div>`:`<div class="empty">Run local analysis for this filing to populate the structured summary and citations.</div>`}</div></div><details><summary>Source documents and filing links</summary><div class="source-links">${links||'<span class="empty">No source links stored for this filing yet.</span>'}</div></details>`;root.appendChild(card)})}
    async function loadCompanies(){const res=await fetch("/api/v1/companies"),data=await res.json();companies=data.companies||[];renderStats();renderList();const params=new URLSearchParams(window.location.search),requested=(params.get("ticker")||"").toUpperCase(),preferred=companies.find(c=>c.ticker===requested)||companies.find(c=>c.analyzed_count>0)||companies[0];if(preferred)await loadWorkspace(preferred.ticker)}
    async function loadWorkspace(ticker){selectedTicker=ticker;renderList();const res=await fetch(`/api/v1/companies/${ticker}/workspace`),data=await res.json();if(!res.ok)return;const params=new URLSearchParams(window.location.search);params.set("ticker",ticker);window.history.replaceState({}, "", `/?${params.toString()}`);renderMarket(data.company,data.market||{},data.coverage||{});renderSummary(data.summary||{sections:[]});renderFilings(data.filings||[])}
    searchEl.addEventListener("input",renderList);withFilingsEl.addEventListener("change",renderList);loadCompanies();
  </script>
</body>
</html>"""
    return Response(html, mimetype="text/html")
