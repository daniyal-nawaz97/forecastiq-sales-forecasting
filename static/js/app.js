/* ForecastIQ front-end */
Object.assign(ICONS, {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/>',
  sliders: '<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 17v-3"/><path d="M12 17v-6"/><path d="M15 17v-4"/>',
  trendUp: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
});

const App = { user: null, info: null };
const canEdit = () => ["admin", "analyst"].includes(App.user?.role);
const isAdmin = () => App.user?.role === "admin";
const rs = (v, d = 1) => {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v);
  return a >= 1e6 ? `Rs. ${(v / 1e6).toFixed(d === 1 ? 2 : d)}M` : a >= 1e3 ? `Rs. ${Math.round(v / 1e3).toLocaleString()}k` : `Rs. ${Math.round(v)}`;
};
const pct = (v) => (v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`);
const tip = (t) => `<div class="tip">${icon("lightbulb")}<span>${t}</span></div>`;
const monthName = (m) => new Date(m + "-01T00:00:00").toLocaleDateString("en-GB", { month: "long", year: "numeric" });
const loadChart = () => (window.Chart ? Promise.resolve() : new Promise((r) => { window.addEventListener("load", r, { once: true }); setTimeout(r, 4000); }));
const accent = () => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0d9488";

function brandHTML() {
  const i = App.info || {};
  return `<a class="brand" href="#/">${i.logo_url ? `<img src="${esc(i.logo_url)}" alt="logo">` : `<span class="brand-mark">${icon("trendUp")}</span>`}<span>ForecastIQ</span>
    ${i.company_name ? `<span class="hide-sm" style="font-weight:500;color:var(--text-3);font-size:14px">· ${esc(i.company_name)}</span>` : ""}</a>`;
}

function shell(active, html, { wide = true } = {}) {
  const nav = [["overview", "#/", "grid", "Overview"], ["forecast", "#/forecast", "chart", "Forecast"], ["products", "#/products", "box", "Products"],
    ["scenarios", "#/scenarios", "sliders", "Scenarios"], ["accuracy", "#/accuracy", "target", "Accuracy"], ["data", "#/data", "db", "Data"], ["reports", "#/reports", "report", "Reports"]];
  if (isAdmin()) nav.push(["settings", "#/settings", "settings", "Settings"]);
  const isDemo = !!App.info?.dataset?.is_demo;
  $("#app").innerHTML = `
    ${isDemo ? `<div class="demo-banner">Demo company: Sahara Mart is fictitious. Its sales history is clearly labelled sample data.</div>` : ""}
    <header class="topbar">${brandHTML()}
      <nav class="nav" aria-label="Main">${nav.map(([k, h, ic, l]) => `<a href="${h}" class="${active === k ? "active" : ""}">${icon(ic)}${l}</a>`).join("")}</nav>
      <div class="spacer"></div>
      <div class="profile"><button class="avatar" id="avatarBtn" aria-label="Profile menu">${esc(initials(App.user?.name))}</button>
        <div class="menu hidden" id="profileMenu"><div class="menu-head"><div style="font-weight:600">${esc(App.user?.name)}</div><div class="muted small">${esc(App.user?.email)}</div><div class="tiny muted" style="text-transform:capitalize">${esc(App.user?.role)}</div></div>
          <a href="#/data">${icon("db")} Data &amp; uploads</a><a href="/privacy" target="_blank">${icon("shield")} Privacy</a><button id="logoutBtn">${icon("logout")} Sign out</button></div></div>
    </header>
    <main class="page ${wide ? "wide" : ""}" id="main">${html}</main>
    <nav class="bottom-nav" aria-label="Main">${[nav[0], nav[1], nav[2], nav[3], nav[6]].map(([k, h, ic, l]) => `<a href="${h}" class="${active === k ? "active" : ""}">${icon(ic)}${l}</a>`).join("")}</nav>`;
  document.body.style.setProperty("--banner-h", isDemo ? "32px" : "0px");
  $("#avatarBtn").onclick = (e) => { e.stopPropagation(); $("#profileMenu").classList.toggle("hidden"); };
  document.addEventListener("click", () => $("#profileMenu")?.classList.add("hidden"));
  $("#logoutBtn").onclick = async () => { await api("/api/logout", { method: "POST" }); App.user = null; location.hash = "#/login"; };
  return $("#main");
}

async function ensureUser() {
  App.info = await api("/api/app-info");
  setAccent(App.info.accent_color);
  if (!App.user) App.user = await api("/api/me");
  return App.user;
}

/* Not-ready / no-data states shared by data screens */
async function guarded(active, fn) {
  try { return await fn(); }
  catch (e) {
    if (e.status === 409) shell(active, `<div class="card"><div class="empty"><div class="empty-icon">${icon("db")}</div><h3>No sales data yet</h3><p>Upload 12-24 months of sales (Excel or CSV) and your forecast appears here.</p>
      <a class="btn btn-primary" href="#/data">${icon("upload")} Upload sales data</a> <a class="btn" href="/api/sample.csv">Download sample data</a></div></div>`);
    else if (e.status === 503) { shell(active, `<div class="card"><div class="empty"><div class="spinner" style="margin:0 auto 12px;width:28px;height:28px"></div><h3>Preparing your forecast…</h3><p>Testing several forecasting methods on your past months. This takes a few seconds.</p></div></div>`); setTimeout(() => Router.go(), 2500); }
    else throw e;
  }
}

/* ---------- chart: solid = actual, dotted = forecast, shaded = likely range, flags = events ---------- */
const flagPlugin = {
  id: "flags",
  afterDatasetsDraw(chart, _, opts) {
    const { ctx, chartArea, scales } = chart;
    const evs = opts.events || [];
    let lastX = -999;
    ctx.save();
    const xs = evs.map((ev) => scales.x.getPixelForValue(ev.idx));
    xs.forEach((x) => {
      if (x < chartArea.left || x > chartArea.right) return;
      ctx.strokeStyle = "rgba(245,158,11,.55)"; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(x, chartArea.top + 14); ctx.lineTo(x, chartArea.bottom); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = "#f59e0b";
      ctx.beginPath(); ctx.arc(x, chartArea.top + 10, 4, 0, Math.PI * 2); ctx.fill();
    });
    ctx.font = "600 11px Inter, sans-serif"; ctx.textAlign = "left";
    evs.forEach((ev, i) => {
      const x = xs[i];
      if (x < chartArea.left || x > chartArea.right || x - lastX < 90) return;
      const label = ev.name.length > 16 ? ev.name.slice(0, 15) + "…" : ev.name;
      const tx = Math.min(x + 7, chartArea.right - ctx.measureText(label).width - 4);
      ctx.fillStyle = "rgba(255,255,255,.9)"; ctx.fillRect(tx - 2, chartArea.top + 4, ctx.measureText(label).width + 4, 13);
      ctx.fillStyle = "#92400e"; ctx.fillText(label, tx, chartArea.top + 14);
      lastX = x;
    });
    ctx.restore();
  },
};

function forecastChart(canvas, history, forecast, events, view = "weekly") {
  const labels = [...history.map((h) => h.t), ...forecast.map((f) => f.t)];
  const n = history.length;
  const last = history[n - 1];
  const pad = (arr) => Array(n - 1).fill(null).concat(arr);
  const fcLine = pad([last?.v, ...forecast.map((f) => f.v)]);
  const lo = pad([last?.v, ...forecast.map((f) => f.low)]);
  const hi = pad([last?.v, ...forecast.map((f) => f.high)]);
  const idxOf = (d) => { let best = 0; labels.forEach((l, i) => { if (l <= d) best = i; }); return best; };
  const flags = [];
  const seen = new Set();
  for (const e of events) { const key = e.name + e.date.slice(0, 7); if (!seen.has(key)) { seen.add(key); flags.push({ idx: idxOf(e.date), name: e.name }); } }
  const a = accent();
  const fmtLabel = (t) => { const d = new Date(t + "T00:00:00"); return view === "monthly" ? d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }) : d.toLocaleDateString("en-GB", { day: "numeric", month: "short" }); };
  return new Chart(canvas, {
    type: "line",
    data: { labels: labels.map(fmtLabel), datasets: [
      { label: "Actual", data: history.map((h) => h.v).concat(Array(forecast.length).fill(null)), borderColor: "#111827", borderWidth: 2.2, pointRadius: 0, tension: 0.25 },
      { label: "Likely range (low)", data: lo, borderColor: "transparent", pointRadius: 0, fill: false, tension: 0.25 },
      { label: "Likely range", data: hi, borderColor: "transparent", backgroundColor: a + "33", pointRadius: 0, fill: "-1", tension: 0.25 },
      { label: "Forecast", data: fcLine, borderColor: a, borderDash: [6, 5], borderWidth: 2.5, pointRadius: view === "monthly" ? 3 : 0, pointBackgroundColor: a, tension: 0.25 },
    ] },
    options: { maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, flags: { events: flags },
        tooltip: { filter: (i) => i.datasetIndex !== 1 && i.parsed.y !== null && !(i.datasetIndex === 2), callbacks: {
          label: (c) => c.datasetIndex === 3 ? `Forecast: ${rs(c.parsed.y)} (range ${rs(lo[c.dataIndex])} – ${rs(hi[c.dataIndex])})` : `${c.dataset.label}: ${rs(c.parsed.y)}` } } },
      scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10, maxRotation: 0 } }, y: { grid: { color: "#eef0f3" }, ticks: { callback: (v) => rs(v, 1) } } } },
    plugins: [flagPlugin],
  });
}
const chartLegend = `<div class="legend-line"><span><i></i>Actual</span><span><i class="dot"></i>Forecast</span><span><i class="band"></i>Likely range (8 in 10 outcomes)</span><span><i class="flag"></i>Ramadan, Eid &amp; promotions</span></div>`;

function spark(values, split) {
  const w = 120, h = 32, max = Math.max(...values), min = Math.min(...values);
  const x = (i) => (i / (values.length - 1)) * (w - 4) + 2, y = (v) => h - 3 - ((v - min) / (max - min || 1)) * (h - 6);
  const pts = (arr, off) => arr.map((v, i) => `${x(i + off).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts(values.slice(0, split), 0)}" fill="none" stroke="#111827" stroke-width="1.6"/>
    <polyline points="${pts(values.slice(split - 1), split - 1)}" fill="none" stroke="${accent()}" stroke-width="1.8" stroke-dasharray="3 3"/></svg>`;
}
const riskBadge = (r) => !r ? `<span class="risk r-none">—</span>` : `<span class="risk ${{ "Stock-out risk": "r-out", "Overstock risk": "r-over", Healthy: "r-ok", "Trending down": "r-down", Growing: "r-up", Steady: "r-ok" }[r] || "r-none"}">${esc(r)}</span>`;

/* ---------- login ---------- */
Router.add("/login", async () => {
  App.info = await api("/api/app-info"); setAccent(App.info.accent_color);
  $("#app").innerHTML = `<div class="auth-wrap"><div class="card auth-card">${brandHTML()}
    <h1>See next month's sales</h1><p class="lead">Plan stock and budget with a forecast you can trust, and see why.</p>
    <form id="lf" class="stack" novalidate><label class="field">Email<input class="input" type="email" name="email" autocomplete="username" placeholder="you@company.com"></label>
      <label class="field">Password<input class="input" type="password" name="password" autocomplete="current-password" placeholder="••••••••"></label>
      <div id="le" class="alert err hidden" role="alert"></div><button class="btn btn-primary btn-lg btn-block">Sign in</button></form>
    <div class="divider">or</div><button class="btn btn-lg btn-block" id="demoBtn">${icon("chart")} Explore demo business</button>
    <p class="tiny muted" style="text-align:center;margin-top:10px">A fictitious retail chain with 30 months of sample sales.</p>
    <div class="privacy-line">${icon("lock")}<span>Your sales data stays private. <a href="/privacy" target="_blank">Privacy</a></span></div></div></div>`;
  $("#lf").onsubmit = async (e) => {
    e.preventDefault(); const f = new FormData(e.target);
    try { await api("/api/login", { method: "POST", body: { email: f.get("email"), password: f.get("password") } }); App.user = null; location.hash = sessionStorage.getItem("afterLogin") || "#/"; }
    catch (err) { $("#le").textContent = err.message; $("#le").classList.remove("hidden"); }
  };
  $("#demoBtn").onclick = async () => {
    const b = $("#demoBtn"); b.disabled = true; b.innerHTML = `<span class="spinner"></span> Opening demo business…`;
    for (let i = 0; i < 60; i++) {
      try { await api("/api/demo-login", { method: "POST" }); App.user = null; location.hash = "#/"; return; }
      catch (e) { if (e.status !== 503) { toast(e.message, "err"); break; } b.innerHTML = `<span class="spinner"></span> Preparing forecasts…`; await new Promise((r) => setTimeout(r, 2000)); }
    }
    b.disabled = false; b.innerHTML = `${icon("chart")} Explore demo business`;
  };
});

/* ---------- overview ---------- */
Router.add("/", async () => guarded("overview", async () => {
  await ensureUser();
  const o = await api("/api/overview");
  const c = o.cards;
  shell("overview", `
    <div class="page-head"><div><h1>${esc(c.next_month)} outlook</h1><p>Based on sales up to ${fmt.date(o.data_to, "DD Mon YYYY")}. Forecasts are estimates with a likely range, not promises.</p></div>
      <div class="row wrap"><a class="btn" href="#/scenarios">${icon("sliders")} Try a what-if</a><a class="btn btn-primary" href="#/reports">${icon("report")} Monthly report</a></div></div>
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="card stat"><div class="label">${icon("calendar")} Last month (${esc(c.last_month)})</div><div class="value">${rs(c.last_month_value)}</div><div class="sub">actual sales</div></div>
      <div class="card stat"><div class="label">${icon("trendUp")} ${esc(c.next_month)} forecast</div><div class="value" style="color:var(--accent)">${rs(c.next_value)}</div><div class="sub"><b style="color:${c.growth >= 0 ? "var(--ok)" : "var(--err)"}">${pct(c.growth)}</b> vs last month</div></div>
      <div class="card stat"><div class="label">${icon("sliders")} Likely range</div><div class="value" style="font-size:24px">${rs(c.low)} – ${rs(c.high)}</div><div class="sub">8 in 10 outcomes fall in this range</div></div>
      <a class="card stat good" href="#/accuracy" style="color:inherit;text-decoration:none"><div class="label">${icon("target")} Forecast accuracy</div><div class="value">${c.accuracy ?? "—"}%</div><div class="sub">tested on your last ${c.backtest_months} months</div></a>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Sales history and forecast</h2><span class="small muted">Weekly sales, last 18 months + next 3 months</span></div>
      <div class="chart-box"><canvas id="ch"></canvas></div>${chartLegend}</div>
    <div class="dash-grid">
      <div class="card"><div class="card-head"><h2>What is driving the forecast</h2></div><div class="card-body"><ul class="drv">${o.drivers.map((d) => `<li>${icon("checkCircle")}<span>${esc(d)}</span></li>`).join("")}</ul></div></div>
      <div class="card"><div class="card-head"><h2>Attention</h2><a class="small" href="#/products">All products</a></div><div class="card-body"><ul class="att">
        ${o.attention.length ? o.attention.map((a) => `<li class="a-${a.type}">${icon(a.type === "good" ? "trendUp" : "alert")}<span>${esc(a.text)}</span></li>`).join("") : `<li class="a-good">${icon("check")}<span>No risks spotted. Stock and branches look healthy.</span></li>`}</ul></div></div>
    </div>`);
  await loadChart();
  forecastChart($("#ch"), o.chart.history.map((h) => ({ t: h.week, v: h.value })), o.chart.forecast.map((f) => ({ t: f.week, v: f.value, low: f.low, high: f.high })), o.chart.events);
}));

/* ---------- forecast explorer ---------- */
Router.add("/forecast", async (_, q) => guarded("forecast", async () => {
  await ensureUser();
  const st = { product: q.product || "", category: q.category || "", branch: q.branch || "", horizon: +(q.horizon || 3), view: q.view || "weekly", history: +(q.history ?? 12) };
  const first = await api(`/api/explorer?${new URLSearchParams(st)}`);
  shell("forecast", `
    <div class="page-head"><div><h1>Forecast explorer</h1><p>Pick a product, category or branch, and how far ahead to look.</p></div>
      <a class="btn" id="xl" href="#">${icon("download")} Download forecast (Excel)</a></div>
    <div class="filters">
      <label>Product<select class="input" id="fp"><option value="">All products</option>${first.options.products.map((p) => `<option ${p === st.product ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>
      <label>Category<select class="input" id="fc"><option value="">All categories</option>${first.options.categories.map((p) => `<option ${p === st.category ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>
      <label>Branch<select class="input" id="fb"><option value="">All branches</option>${first.options.branches.map((p) => `<option ${p === st.branch ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>
      <label>Forecast ahead<div class="seg" id="fh">${[1, 3, 6, 12].map((h) => `<button data-v="${h}" class="${h === st.horizon ? "active" : ""}">${h} mo</button>`).join("")}</div></label>
      <label>View<div class="seg" id="fv">${[["daily", "Daily"], ["weekly", "Weekly"], ["monthly", "Monthly"]].map(([k, l]) => `<button data-v="${k}" class="${k === st.view ? "active" : ""}">${l}</button>`).join("")}</div></label>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="card-head"><h2 id="ttl"></h2><div class="row"><span class="small muted" id="meth"></span><select class="input" id="hist" style="width:150px;height:34px">
      ${[[6, "Last 6 months"], [12, "Last 12 months"], [24, "Last 24 months"], [0, "All history"]].map(([v, l]) => `<option value="${v}" ${v === st.history ? "selected" : ""}>${l}</option>`).join("")}</select></div></div>
      <div class="chart-box"><canvas id="ch"></canvas></div>${chartLegend}</div>
    <div class="dash-grid"><div class="card"><div class="card-head"><h2>Forecast by month</h2></div><div class="table-wrap"><table class="table"><thead><tr><th>Month</th><th class="right">Low</th><th class="right">Expected</th><th class="right">High</th></tr></thead><tbody id="tb"></tbody></table></div></div>
      <div class="card"><div class="card-head"><h2>Why</h2></div><div class="card-body"><ul class="drv" id="drv"></ul><div id="exn" style="margin-top:8px"></div></div></div></div>`);
  let chart;
  const render = async (d) => {
    const sel = [st.product, st.category, st.branch].filter(Boolean).join(" · ") || "Whole business";
    $("#ttl").textContent = sel;
    $("#meth").textContent = `Method: ${d.method === "regression" ? "explainable model" : "Holt-Winters"} · ${d.error != null ? `${(100 - d.error * 100).toFixed(1)}% accurate on recent months` : ""}`;
    $("#tb").innerHTML = d.table.map((m) => `<tr><td>${monthName(m.month)}</td><td class="right num">${rs(m.low)}</td><td class="right num"><b>${rs(m.expected)}</b></td><td class="right num">${rs(m.high)}</td></tr>`).join("");
    $("#drv").innerHTML = d.drivers.map((x) => `<li>${icon("checkCircle")}<span>${esc(x)}</span></li>`).join("");
    $("#exn").innerHTML = d.excluded_days ? tip(`${d.excluded_days} days (missing data, stock-outs or typing errors) were left out so they don't distort the forecast. See the Data page.`) : "";
    $("#xl").href = `/api/explorer/export.xlsx?${new URLSearchParams({ product: st.product, category: st.category, branch: st.branch, horizon: st.horizon })}`;
    await loadChart();
    chart?.destroy();
    chart = forecastChart($("#ch"), d.history, d.forecast, d.events, st.view);
  };
  const reload = async () => {
    history.replaceState(null, "", "#/forecast?" + new URLSearchParams(st));
    $("#ttl").innerHTML = `<span class="row" style="gap:8px"><span class="spinner"></span>Updating…</span>`;
    try { render(await api(`/api/explorer?${new URLSearchParams(st)}`)); } catch (e) { toast(e.message, "err"); }
  };
  $("#fp").onchange = (e) => { st.product = e.target.value; reload(); };
  $("#fc").onchange = (e) => { st.category = e.target.value; reload(); };
  $("#fb").onchange = (e) => { st.branch = e.target.value; reload(); };
  $("#hist").onchange = (e) => { st.history = +e.target.value; reload(); };
  $$("#fh button").forEach((b) => (b.onclick = () => { st.horizon = +b.dataset.v; $$("#fh button").forEach((x) => x.classList.toggle("active", x === b)); reload(); }));
  $$("#fv button").forEach((b) => (b.onclick = () => { st.view = b.dataset.v; $$("#fv button").forEach((x) => x.classList.toggle("active", x === b)); reload(); }));
  render(first);
}));

/* ---------- products & branches ---------- */
Router.add("/products", async (_, q) => guarded("products", async () => {
  await ensureUser();
  let by = q.by || "product";
  shell("products", `
    <div class="page-head"><div><h1>Products and branches</h1><p>Next month's forecast for each one, with stock-out and overstock risk.</p></div></div>
    <div class="tabs" id="tabs">${[["product", "Products"], ["category", "Categories"], ["branch", "Branches"]].map(([k, l]) => `<button data-b="${k}" class="${k === by ? "active" : ""}">${l}</button>`).join("")}</div>
    <div class="card"><div class="table-wrap"><table class="table"><thead id="th"></thead><tbody id="tb"><tr><td><div class="skeleton" style="height:18px;width:300px"></div></td></tr></tbody></table></div></div>
    <div style="margin-top:12px">${tip("Click a row to open its own forecast. Stock risk compares current stock with the next 30 days of forecast sales (add a stock file on the Data page).")}</div>`);
  const load = async () => {
    const d = await api(`/api/breakdown?by=${by}`);
    const nm = { product: "Product", category: "Category", branch: "Branch" }[by];
    $("#th").innerHTML = `<tr><th>${nm}</th><th class="right">Last month</th><th class="right">Next month</th><th class="right">Change</th><th class="hide-sm">Last 12 months → next 3</th><th>${by === "branch" ? "Trend" : by === "product" ? "Stock" : "Accuracy"}</th></tr>`;
    $("#tb").innerHTML = d.rows.map((r) => `<tr class="clickable" data-n="${esc(r.name)}"><td><b style="font-weight:600">${esc(r.name)}</b>${r.risk_detail?.length ? `<div class="tiny muted">${r.risk_detail.map(esc).join(" · ")}</div>` : ""}</td>
      <td class="right num">${rs(r.last_month)}</td><td class="right num"><b>${rs(r.next_month)}</b></td>
      <td class="right"><span class="arrow ${r.growth >= 0 ? "up" : "down"}">${r.growth >= 0 ? "▲" : "▼"} ${Math.abs(r.growth).toFixed(1)}%</span></td>
      <td class="hide-sm">${spark(r.spark, r.spark_split)}</td>
      <td>${by === "category" ? `<span class="small">${r.error != null ? `${(100 - r.error * 100).toFixed(0)}%` : "—"}</span>` : riskBadge(r.risk)}${by === "branch" && r.trend != null ? `<div class="tiny muted">${pct(r.trend)} vs rest of business (3 mo)</div>` : ""}</td></tr>`).join("");
    $$("#tb tr[data-n]").forEach((tr) => (tr.onclick = () => (location.hash = `#/forecast?${new URLSearchParams({ [by]: tr.dataset.n, horizon: 3 })}`)));
  };
  $$("#tabs button").forEach((b) => (b.onclick = () => { by = b.dataset.b; $$("#tabs button").forEach((x) => x.classList.toggle("active", x === b)); history.replaceState(null, "", `#/products?by=${by}`); load(); }));
  load();
}));

/* ---------- scenarios ---------- */
Router.add("/scenarios", async () => guarded("scenarios", async () => {
  await ensureUser();
  const p = { discount: 0, marketing: 0, price: 0, new_branch: false, branch_month: 2, months: 3 };
  const saved = await api("/api/scenarios");
  shell("scenarios", `
    <div class="page-head"><div><h1>What-if scenarios</h1><p>See how a decision could change the next months, before you make it.</p></div><span class="estimate-label">${icon("info")} Scenarios are estimates</span></div>
    <div class="scen-grid">
      <div class="card card-body">
        ${[["discount", "Discount", 0, 30, 1, "%"], ["marketing", "Marketing spend change", -50, 100, 5, "%"], ["price", "Price increase", 0, 20, 1, "%"]].map(([k, l, mi, ma, stp, u]) => `
          <div class="slider"><div class="row"><span>${l}</span><span class="val" id="v_${k}">0${u}</span></div><input type="range" id="s_${k}" min="${mi}" max="${ma}" step="${stp}" value="0" aria-label="${l}"></div>`).join("")}
        <label class="row" style="gap:10px;margin-bottom:10px;font-weight:600"><span class="switch"><input type="checkbox" id="s_nb"><span></span></span>A new branch opens</label>
        <div id="nbm" class="hidden" style="margin-bottom:18px"><label class="field">Opens in month<select class="input" id="s_bm">${[1, 2, 3].map((m) => `<option value="${m}" ${m === 2 ? "selected" : ""}>${m}</option>`).join("")}</select></label></div>
        <label class="field" style="margin-bottom:18px">Look ahead<select class="input" id="s_mo"><option value="3">3 months</option><option value="6">6 months</option><option value="12">12 months</option></select></label>
        <div class="row wrap"><button class="btn" id="reset">Reset</button>${canEdit() ? `<button class="btn btn-primary" id="save">${icon("check")} Save &amp; share</button>` : ""}</div>
      </div>
      <div class="stack">
        <div class="summary-card" id="sum">Move a slider to see how a decision could change the next months.</div>
        <div class="grid grid-4" id="nums"></div>
        <div class="card"><div class="card-head"><h2>Baseline vs your scenario</h2></div><div class="chart-box sm"><canvas id="ch"></canvas></div>
          <div class="legend-line"><span><i class="dot"></i>Baseline forecast</span><span><i style="border-color:#f59e0b"></i>Your scenario</span><span><i class="band"></i>Baseline likely range</span></div></div>
        <div class="card card-body"><b class="small">How this is estimated</b><ul class="small muted" id="assume" style="margin:6px 0 0;padding-left:18px"></ul></div>
        <div class="card"><div class="card-head"><h2>Saved scenarios</h2></div><div id="saved">${savedHTML(saved)}</div></div>
      </div></div>`);
  let chart, timer;
  const run = async () => {
    const r = await api("/api/scenario", { method: "POST", body: p });
    $("#sum").textContent = r.summary;
    const t = r.totals, dr = t.scen_rev - t.base_rev, dm = t.scen_margin - t.base_margin;
    $("#nums").innerHTML = [["Baseline revenue", rs(t.base_rev), ""], ["Scenario revenue", rs(t.scen_rev), dr], ["Baseline margin", rs(t.base_margin), ""], ["Scenario margin", rs(t.scen_margin), dm]]
      .map(([l, v, d]) => `<div class="card stat"><div class="label">${l}</div><div class="value" style="font-size:22px">${v}</div><div class="sub">${d === "" ? "&nbsp;" : `<b style="color:${d >= 0 ? "var(--ok)" : "var(--err)"}">${d >= 0 ? "+" : "−"}${rs(Math.abs(d))}</b>`}</div></div>`).join("");
    $("#assume").innerHTML = r.assumptions.map((a) => `<li>${esc(a)}</li>`).join("");
    await loadChart(); chart?.destroy();
    const a = accent();
    chart = new Chart($("#ch"), { type: "line", data: { labels: r.rows.map((x) => monthName(x.month).slice(0, 3) + " " + x.month.slice(2, 4)), datasets: [
      { label: "Low", data: r.rows.map((x) => x.low), borderColor: "transparent", pointRadius: 0 },
      { label: "High", data: r.rows.map((x) => x.high), borderColor: "transparent", backgroundColor: a + "26", fill: "-1", pointRadius: 0 },
      { label: "Baseline", data: r.rows.map((x) => x.baseline), borderColor: a, borderDash: [6, 5], borderWidth: 2.5, pointRadius: 3, pointBackgroundColor: a },
      { label: "Your scenario", data: r.rows.map((x) => x.scenario), borderColor: "#f59e0b", borderWidth: 3, pointRadius: 4, pointBackgroundColor: "#f59e0b" }] },
      options: { maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { display: false },
        tooltip: { filter: (i) => i.datasetIndex >= 2, callbacks: { label: (c) => `${c.dataset.label}: ${rs(c.parsed.y)}` } } },
        scales: { x: { grid: { display: false } }, y: { grid: { color: "#eef0f3" }, ticks: { callback: (v) => rs(v) } } } } });
  };
  const upd = () => { clearTimeout(timer); timer = setTimeout(run, 150); };
  ["discount", "marketing", "price"].forEach((k) => ($(`#s_${k}`).oninput = (e) => { p[k] = +e.target.value; $(`#v_${k}`).textContent = `${p[k] > 0 && k === "marketing" ? "+" : ""}${p[k]}%`; upd(); }));
  $("#s_nb").onchange = (e) => { p.new_branch = e.target.checked; $("#nbm").classList.toggle("hidden", !p.new_branch); upd(); };
  $("#s_bm").onchange = (e) => { p.branch_month = +e.target.value; upd(); };
  $("#s_mo").onchange = (e) => { p.months = +e.target.value; upd(); };
  $("#reset").onclick = () => { Object.assign(p, { discount: 0, marketing: 0, price: 0, new_branch: false }); ["discount", "marketing", "price"].forEach((k) => { $(`#s_${k}`).value = 0; $(`#v_${k}`).textContent = "0%"; }); $("#s_nb").checked = false; $("#nbm").classList.add("hidden"); run(); };
  $("#save") && ($("#save").onclick = () => modal({ title: "Save scenario", confirm: "Save", body: `<label class="field">Name<input class="input" id="sn" placeholder="e.g. 15% discount in December"></label>`,
    onConfirm: async (m) => { await api("/api/scenarios", { method: "POST", body: { ...p, name: $("#sn", m).value } }); $("#saved").innerHTML = savedHTML(await api("/api/scenarios")); bindSaved(); toast("Scenario saved. Your team can see it here."); } }));
  const bindSaved = () => {
    $$("[data-load]").forEach((b) => (b.onclick = () => { const s = saved.concat([]).find((x) => x.id === +b.dataset.load) || {}; }));
    $$("[data-sdel]").forEach((b) => (b.onclick = async () => { await api(`/api/scenarios/${b.dataset.sdel}`, { method: "DELETE" }); $("#saved").innerHTML = savedHTML(await api("/api/scenarios")); bindSaved(); }));
    $$("[data-apply]").forEach((b) => (b.onclick = () => {
      const sp = JSON.parse(b.dataset.apply);
      Object.assign(p, sp);
      ["discount", "marketing", "price"].forEach((k) => { $(`#s_${k}`).value = p[k]; $(`#v_${k}`).textContent = `${p[k]}%`; });
      $("#s_nb").checked = !!p.new_branch; $("#nbm").classList.toggle("hidden", !p.new_branch); $("#s_mo").value = p.months; run();
    }));
  };
  bindSaved();
  run();
}));
function savedHTML(list) {
  return list.length ? list.map((s) => `<div class="member" style="padding:12px 18px"><div class="grow"><b style="font-weight:600">${esc(s.name)}</b><div class="small muted">${esc(s.summary || "")}</div><div class="tiny muted">${esc(s.created_by || "")} · ${fmt.when(s.created_at)}</div></div>
    <button class="btn btn-sm" data-apply='${esc(JSON.stringify(s.params))}'>Open</button>${canEdit() ? `<button class="btn btn-ghost icon-btn btn-sm" data-sdel="${s.id}" aria-label="Delete">${icon("trash")}</button>` : ""}</div>`).join("")
    : `<div class="card-body small muted">No saved scenarios yet. Try one, then press <b>Save &amp; share</b>.</div>`;
}

/* ---------- accuracy ---------- */
Router.add("/accuracy", async () => guarded("accuracy", async () => {
  await ensureUser();
  const a = await api("/api/accuracy");
  const best = a.methods.find((m) => m.chosen);
  shell("accuracy", `
    <div class="page-head"><div><h1>How well would we have predicted the past?</h1><p>We test the forecast on your own past months, so you can see how reliable it is.</p></div></div>
    <div class="grid grid-4" style="margin-bottom:16px">
      <div class="card stat"><div class="label">Average error</div><div class="score-big">${(a.error * 100).toFixed(1)}%</div><div class="sub">per month, last ${a.rows.length} months</div></div>
      <div class="card stat good"><div class="label">Better than a simple guess</div><div class="score-big">${a.improvement != null ? `${Math.round(a.improvement * 100)}%` : "—"}</div><div class="sub">${esc(a.simple_method || "")} was off by ${a.simple_error != null ? (a.simple_error * 100).toFixed(1) + "%" : "—"}</div></div>
      <div class="card stat"><div class="label">Inside the likely range</div><div class="score-big">${a.within_range ?? "—"}%</div><div class="sub">of tested months</div></div>
      <div class="card stat"><div class="label">Method used</div><div class="value" style="font-size:17px;margin-top:10px">${esc(best?.name || "")}</div><div class="sub">chosen because it was most accurate</div></div>
    </div>
    <div class="card" style="margin-bottom:16px"><div class="card-head"><h2>Forecast made beforehand vs what really happened</h2><span class="small muted">Each forecast used only data available before that month</span></div>
      <div class="chart-box sm"><canvas id="ch"></canvas></div></div>
    <div class="dash-grid">
      <div class="card"><div class="card-head"><h2>Methods compared</h2></div><div class="table-wrap"><table class="table"><thead><tr><th>Method</th><th class="right">Average error</th></tr></thead><tbody>
        ${a.methods.map((m) => `<tr><td>${esc(m.name)} ${m.chosen ? `<span class="badge ok plain">Used</span>` : ""}</td><td class="right num"><b>${m.error != null ? (m.error * 100).toFixed(1) + "%" : "—"}</b></td></tr>`).join("")}</tbody></table></div></div>
      <div class="card"><div class="card-head"><h2>By product</h2><span class="small muted">Which are easy or hard to forecast</span></div><div class="table-wrap"><table class="table"><thead><tr><th>Product</th><th class="right">Error</th><th>How predictable</th></tr></thead><tbody>
        ${a.products.map((p) => `<tr><td>${esc(p.product)}</td><td class="right num">${p.error != null ? (p.error * 100).toFixed(1) + "%" : "—"}</td><td><span class="risk ${p.label === "Easy to forecast" ? "r-ok" : p.label === "Moderate" ? "r-over" : "r-out"}">${esc(p.label || "—")}</span></td></tr>`).join("")}</tbody></table></div></div>
    </div>
    <div style="margin-top:14px">${tip("Seasonal products with big Ramadan or summer peaks are harder to predict. More history (24+ months) and marking promotions in Settings → Events improve results.")}</div>`);
  await loadChart();
  const a2 = accent();
  new Chart($("#ch"), { type: "bar", data: { labels: a.rows.map((r) => monthName(r.month)), datasets: [
    { label: "Actual", data: a.rows.map((r) => r.actual), backgroundColor: "#111827", borderRadius: 4, barPercentage: 0.7 },
    { label: "Forecast made beforehand", data: a.rows.map((r) => r[a.best]), backgroundColor: a2, borderRadius: 4, barPercentage: 0.7 },
    { label: "Simple guess", data: a.rows.map((r) => r[a.simple_method && a.simple_method.includes("last year") ? "last_year" : "last_month"]), backgroundColor: "#cbd5e1", borderRadius: 4, barPercentage: 0.7 }] },
    options: { maintainAspectRatio: false, animation: false, plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${rs(c.parsed.y)}` } } },
      scales: { x: { grid: { display: false } }, y: { grid: { color: "#eef0f3" }, ticks: { callback: (v) => rs(v) } } } } });
}));

/* ---------- data upload & health ---------- */
Router.add("/data", async () => {
  await ensureUser();
  const list = await api("/api/datasets");
  const act = list.find((d) => d.active);
  const h = act?.health || {};
  shell("data", `
    <div class="page-head"><div><h1>Data</h1><p>Upload your sales history. We clean it automatically and tell you exactly what we changed.</p></div></div>
    ${canEdit() ? `<div class="dz" id="dz"><div style="font-weight:650;font-size:16px">${icon("upload")} Drop your sales file here (Excel or CSV)</div>
      <p class="small muted" style="margin:6px 0 14px">Columns: date, product, branch, quantity, revenue (category, unit_cost and ad_spend are optional). <a href="/api/template.csv">Download our sample format</a> · <a href="/api/sample.csv">example file</a></p>
      <div class="row wrap" style="justify-content:center"><label class="btn btn-primary">${icon("files")} Choose sales file<input type="file" id="fin" accept=".csv,.xlsx,.xls" hidden></label>
        <label class="btn">${icon("box")} Add stock file (optional)<input type="file" id="sin" accept=".csv" hidden></label></div><div class="small muted" id="picked" style="margin-top:8px"></div></div>` : ""}
    ${act ? `<div class="card" style="margin-top:16px"><div class="card-head"><h2>Data health check</h2><span class="small muted">${esc(act.name)}${act.is_demo ? ` <span class="badge info plain">Sample data</span>` : ""}</span></div><div class="card-body">
      <div class="health-grid"><div><b>${(h.rows_read || 0).toLocaleString()}</b><span>rows read</span></div><div><b>${fmt.date(h.date_from, "DD Mon YYYY")} – ${fmt.date(h.date_to, "DD Mon YYYY")}</b><span>${h.months} months of history</span></div>
        <div><b>${h.products} · ${h.branches}</b><span>products · branches</span></div><div><b>${h.missing_days ?? 0}</b><span>missing days found</span></div>
        <div><b>${h.duplicates_removed ?? 0}</b><span>duplicates removed</span></div><div><b>${h.unusual_values ?? 0}</b><span>unusual values found</span></div>
        <div><b>${h.stockout_streaks ?? 0}</b><span>possible stock-outs</span></div><div><b>${rs(h.total_revenue)}</b><span>total sales</span></div></div>
      ${(h.messages || []).map((m) => `<div class="msg ${m.level}">${icon(m.level === "ok" ? "checkCircle" : m.level === "ask" ? "info" : m.level === "warn" ? "alert" : "info")}<div>${esc(m.text)}
        ${m.options && canEdit() ? `<div class="choices">${m.options.map(([v, l]) => `<button class="btn btn-sm ${m.choice === v ? "btn-primary" : ""}" data-dec="${v}">${esc(l)}</button>`).join("")}</div>` : ""}</div></div>`).join("")}
      <div style="margin-top:14px">${tip("Changing an answer re-cleans the data and refreshes every forecast.")}</div></div></div>` : ""}
    <div class="card" style="margin-top:16px"><div class="card-head"><h2>Uploaded datasets</h2></div>
      ${list.length ? list.map((d) => `<div class="member" style="padding:12px 18px"><span class="avatar" style="cursor:default;border-radius:10px">${icon("db")}</span><div class="grow"><b style="font-weight:600">${esc(d.name)}</b>
        <div class="small muted">${(d.health.rows_read || 0).toLocaleString()} rows · ${d.health.months} months · uploaded ${fmt.when(d.created_at)}${d.uploaded_by ? ` by ${esc(d.uploaded_by)}` : ""}</div></div>
        ${d.active ? `<span class="badge ok">In use</span>` : canEdit() ? `<button class="btn btn-sm" data-act="${d.id}">Use this data</button>` : ""}
        ${isAdmin() && !d.active ? `<button class="btn btn-ghost icon-btn btn-sm" data-del="${d.id}" aria-label="Delete">${icon("trash")}</button>` : ""}</div>`).join("") : `<div class="card-body muted">No data yet.</div>`}</div>
    <p class="small muted" style="margin-top:12px">Live connections (Google Sheets, online store, accounting system) can be added as part of the Enterprise plan.</p>`, { wide: false });
  let salesFile = null, stockFile = null;
  const go = async () => {
    if (!salesFile) return;
    const fd = new FormData(); fd.append("file", salesFile); if (stockFile) fd.append("stock", stockFile);
    $("#picked").innerHTML = `<span class="row" style="gap:8px;justify-content:center"><span class="spinner"></span>Reading and cleaning ${esc(salesFile.name)}…</span>`;
    try { await api("/api/datasets", { method: "POST", form: fd }); toast("Data uploaded. Building your forecast…"); Router.go(); }
    catch (e) { $("#picked").textContent = ""; toast(e.message, "err", 6000); }
  };
  if ($("#dz")) {
    $("#fin").onchange = (e) => { salesFile = e.target.files[0]; go(); };
    $("#sin").onchange = (e) => { stockFile = e.target.files[0]; $("#picked").textContent = `Stock file ready: ${stockFile.name}. Now choose the sales file.`; };
    const dz = $("#dz");
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => { salesFile = e.dataTransfer.files[0]; go(); });
  }
  $$("[data-dec]").forEach((b) => (b.onclick = async () => { b.disabled = true; await api(`/api/datasets/${act.id}/decision`, { method: "POST", body: { key: "missing", value: b.dataset.dec } }); toast("Thanks. Data re-cleaned and forecasts refreshed."); Router.go(); }));
  $$("[data-act]").forEach((b) => (b.onclick = async () => { await api(`/api/datasets/${b.dataset.act}/activate`, { method: "POST" }); toast("Switched data. Forecasts refreshing…"); Router.go(); }));
  $$("[data-del]").forEach((b) => (b.onclick = async () => { if (await modal({ title: "Delete dataset?", body: "<p>This removes the uploaded file and its cleaned data.</p>", confirm: "Delete", danger: true })) { await api(`/api/datasets/${b.dataset.del}`, { method: "DELETE" }); Router.go(); } }));
});

/* ---------- reports ---------- */
Router.add("/reports", async () => guarded("reports", async () => {
  await ensureUser();
  const [d, s] = await Promise.all([api("/api/reports"), api("/api/settings")]);
  let active = d.reports[0];
  shell("reports", `
    <div class="page-head"><div><h1>Monthly forecast report</h1><p>One click: summary, chart, drivers, risks and product table, as PDF. Plus Excel with all numbers.</p></div>
      ${canEdit() ? `<button class="btn btn-primary" id="mk">${icon("refresh")} Create report now</button>` : ""}</div>
    <div class="reports-grid"><div class="stack">
      <div class="card"><div class="card-head"><h2>Reports</h2><span class="small muted">${d.email_connected ? "Emailed automatically" : "Email not connected: reports stay here"}</span></div>
        <div id="rl">${d.reports.map((r) => `<div class="member" style="padding:12px 18px"><span class="avatar" style="cursor:default;border-radius:10px">${icon("report")}</span><div class="grow"><b style="font-weight:600">${esc(r.title)}</b>
          <div class="small muted">${r.sent_to ? `Sent to ${esc(r.sent_to)}` : "Not sent yet"} · ${fmt.when(r.created_at)}</div></div>
          <a class="btn btn-sm" href="/api/reports/${r.id}/pdf">${icon("download")} PDF</a><a class="btn btn-sm" href="/api/reports/${r.id}/xlsx">Excel</a>
          ${canEdit() ? `<button class="btn btn-sm" data-send="${r.id}">${icon("mail")} Send</button>` : ""}</div>`).join("") || `<div class="card-body muted">No reports yet.</div>`}</div></div>
      <div class="card card-body stack"><h3>Schedule</h3>
        <div class="grid grid-2"><label class="field">Email the report on day<select class="input" id="rd">${[1, 2, 3, 5, 7].map((x) => `<option ${+s.report_day === x ? "selected" : ""}>${x}</option>`).join("")}</select></label>
          <label class="field">of every month, to<input class="input" id="rr" value="${esc(s.report_recipients.join(", "))}"></label></div>
        ${isAdmin() ? `<div><button class="btn btn-primary" id="sv">Save schedule</button></div>` : ""}</div></div>
      <div><b style="display:block;margin-bottom:10px">Email preview</b><div class="phone"><iframe id="pv" title="Email preview"></iframe></div></div></div>`);
  if (active) $("#pv").src = `/api/reports/${active.id}/html`;
  $("#mk") && ($("#mk").onclick = async () => { $("#mk").disabled = true; $("#mk").innerHTML = `<span class="spinner"></span> Building…`; await api("/api/reports", { method: "POST" }); toast("Report ready"); Router.go(); });
  $$("[data-send]").forEach((b) => (b.onclick = async () => { const r = await api(`/api/reports/${b.dataset.send}/send`, { method: "POST" }); toast(r.sent_to === "outbox" ? "Email isn't connected yet; download the PDF instead." : `Sent to ${r.sent_to}`, r.sent_to === "outbox" ? "warn" : "ok", 4500); }));
  $("#sv") && ($("#sv").onclick = async () => { await api("/api/settings", { method: "PUT", body: { report_day: +$("#rd").value, report_recipients: $("#rr").value.split(",").map((x) => x.trim()).filter(Boolean) } }); toast("Schedule saved"); });
}));

/* ---------- settings ---------- */
Router.add("/settings", async (_, q) => {
  await ensureUser();
  if (!isAdmin()) { location.hash = "#/"; return; }
  let s = await api("/api/settings");
  let tab = q.tab || "general";
  shell("settings", `<div class="settings-layout"><div class="page-head"><div><h1>Settings</h1><p>Business details, events calendar, alerts, team and branding.</p></div></div>
    <div class="tabs" id="tabs">${[["general", "General"], ["events", "Holidays & events"], ["team", "Team"], ["branding", "Branding"]].map(([k, l]) => `<button data-t="${k}" class="${k === tab ? "active" : ""}">${l}</button>`).join("")}</div><div id="tb"></div></div>`, { wide: false });
  const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const save = async (patch) => { try { s = await api("/api/settings", { method: "PUT", body: patch }); toast("Saved"); return true; } catch (e) { toast(e.message, "err"); return false; } };
  const render = async () => {
    $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.t === tab));
    if (tab === "general") {
      $("#tb").innerHTML = `<div class="card card-body stack" style="gap:18px"><label class="field">Business name<input class="input" id="cn" value="${esc(s.company_name)}"></label>
        <div class="grid grid-2"><label class="field">Currency label<input class="input" id="cur" value="${esc(s.currency)}"></label>
          <label class="field">Financial year starts in<select class="input" id="fy">${months.map((m, i) => `<option value="${i + 1}" ${+s.fy_start_month === i + 1 ? "selected" : ""}>${m}</option>`).join("")}</select></label></div>
        <label class="field" style="max-width:420px">Warn me if a month's sales fall more than this % below forecast<input class="input" type="number" id="thr" min="1" max="60" value="${s.alert_threshold}"></label>
        <div><button class="btn btn-primary" id="sv">Save</button></div></div>`;
      $("#sv").onclick = () => save({ company_name: $("#cn").value.trim(), currency: $("#cur").value.trim() || "Rs.", fy_start_month: +$("#fy").value, alert_threshold: +$("#thr").value });
    }
    if (tab === "events") {
      const evs = await api("/api/events");
      const upcoming = evs.filter((e) => e.end >= new Date().toISOString().slice(0, 10) || e.source === "custom");
      $("#tb").innerHTML = `<div class="card"><div class="card-head"><h2>Holidays &amp; events</h2><button class="btn btn-sm btn-primary" id="addE">${icon("plus")} Add campaign or event</button></div>
        <div class="table-wrap"><table class="table"><thead><tr><th>Event</th><th>Dates</th><th>Type</th><th></th></tr></thead><tbody>
        ${upcoming.map((e) => `<tr><td><b style="font-weight:600">${esc(e.name)}</b></td><td class="nowrap">${fmt.date(e.start, "DD Mon YYYY")}${e.end !== e.start ? ` – ${fmt.date(e.end, "DD Mon YYYY")}` : ""}</td>
          <td><span class="badge ${e.kind === "promotion" ? "info" : "neutral"} plain">${esc(e.kind.replace("_", " "))}${e.discount ? ` · ${Math.round(e.discount * 100)}% off` : ""}</span></td>
          <td class="right"><button class="btn btn-ghost icon-btn btn-sm" data-ed="${e.id}" aria-label="Delete">${icon("trash")}</button></td></tr>`).join("")}</tbody></table></div></div>
        <div style="margin-top:12px">${tip("Mark past promotions, price changes and new-branch openings too: the forecast learns from them instead of being confused by them. Islamic dates may shift by a day.")}</div>`;
      $("#addE").onclick = () => modal({ title: "Add campaign or event", confirm: "Add", body: `<div class="stack"><label class="field">Name<input class="input" id="en" placeholder="e.g. Winter Sale"></label>
        <div class="grid grid-2"><label class="field">Start<input class="input" type="date" id="es"></label><label class="field">End<input class="input" type="date" id="ee"></label></div>
        <div class="grid grid-2"><label class="field">Type<select class="input" id="ek"><option value="promotion">Promotion / sale</option><option value="holiday">Holiday</option></select></label>
        <label class="field">Discount % (promotions)<input class="input" type="number" id="ed" value="10" min="0" max="90"></label></div></div>`,
        onConfirm: async (m) => { await api("/api/events", { method: "POST", body: { name: $("#en", m).value, start: $("#es", m).value, end: $("#ee", m).value || $("#es", m).value, kind: $("#ek", m).value, discount: +$("#ed", m).value } }); toast("Event added. Forecasts refresh in a moment."); render(); } });
      $$("[data-ed]").forEach((b) => (b.onclick = async () => { await api(`/api/events/${b.dataset.ed}`, { method: "DELETE" }); render(); }));
    }
    if (tab === "team") {
      const us = await api("/api/users");
      $("#tb").innerHTML = `<div class="card"><div class="card-head"><h2>Team</h2><button class="btn btn-sm btn-primary" id="addU">${icon("plus")} Add person</button></div><div class="card-body">
        ${us.map((u) => `<div class="member"><span class="avatar" style="cursor:default">${esc(initials(u.name))}</span><div class="grow"><b style="font-weight:600">${esc(u.name)}</b><div class="small muted">${esc(u.email)}</div></div>
          ${u.id !== App.user.id ? `<select class="input" style="width:130px;height:34px" data-r="${u.id}">${["admin", "analyst", "viewer"].map((r) => `<option value="${r}" ${u.role === r ? "selected" : ""}>${r[0].toUpperCase() + r.slice(1)}</option>`).join("")}</select>
          <button class="btn btn-ghost icon-btn btn-sm" data-ud="${u.id}" aria-label="Remove">${icon("trash")}</button>` : `<span class="badge neutral plain">You</span>`}</div>`).join("")}</div></div>
        <div style="margin-top:12px">${tip("<b>Admins</b> change everything. <b>Analysts</b> upload data, save scenarios and create reports. <b>Viewers</b> see forecasts and reports.")}</div>`;
      $$("[data-r]").forEach((sel) => (sel.onchange = async () => { await api(`/api/users/${sel.dataset.r}`, { method: "PATCH", body: { role: sel.value } }); toast("Role updated"); }));
      $$("[data-ud]").forEach((b) => (b.onclick = async () => { await api(`/api/users/${b.dataset.ud}`, { method: "DELETE" }); render(); }));
      $("#addU").onclick = () => modal({ title: "Add person", confirm: "Add", body: `<div class="stack"><label class="field">Name<input class="input" id="un"></label><label class="field">Email<input class="input" id="ue"></label>
        <label class="field">Role<select class="input" id="ur"><option value="viewer">Viewer</option><option value="analyst">Analyst</option><option value="admin">Admin</option></select></label></div>`,
        onConfirm: async (m) => { const r = await api("/api/users", { method: "POST", body: { name: $("#un", m).value, email: $("#ue", m).value, role: $("#ur", m).value } }); render();
          setTimeout(() => modal({ title: "Person added", body: `<p>Temporary password: <code style="font-size:16px">${esc(r.temporary_password)}</code></p>`, confirm: "Done", cancel: null }), 50); } });
    }
    if (tab === "branding") {
      $("#tb").innerHTML = `<div class="card card-body stack" style="gap:18px"><div class="row wrap" style="gap:18px"><div class="card" style="width:180px;height:70px;display:grid;place-items:center;background:var(--surface-2)">${s.logo_url ? `<img src="${esc(s.logo_url)}" style="max-height:48px;max-width:150px" alt="Logo">` : `<span class="muted small">No logo yet</span>`}</div>
        <label class="btn">${icon("upload")} Upload logo<input type="file" id="lg" accept=".png,.jpg,.jpeg,.svg,.webp" hidden></label></div>
        <label class="field" style="max-width:200px">Accent colour (screens and PDFs)<input class="input" type="color" id="ac" value="${esc(s.accent_color)}" style="height:42px;padding:3px"></label>
        <div><button class="btn btn-primary" id="sb">Save branding</button></div></div>`;
      $("#ac").oninput = (e) => setAccent(e.target.value);
      $("#sb").onclick = () => save({ accent_color: $("#ac").value });
      $("#lg").onchange = async (e) => { const fd = new FormData(); fd.append("file", e.target.files[0]); try { await api("/api/settings/logo", { method: "POST", form: fd }); Router.go(); } catch (err) { toast(err.message, "err"); } };
    }
  };
  $$("#tabs button").forEach((b) => (b.onclick = () => { tab = b.dataset.t; render(); }));
  render();
});

(async () => {
  try { App.info = await api("/api/app-info"); setAccent(App.info.accent_color); } catch {}
  Router.start();
})();
