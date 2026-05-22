/**
 * app.js — Compliance Orchestration Engine Frontend
 *
 * Connects to your FastAPI backend (server.py).
 * Expected endpoints:
 *   POST /audit          → { job_id: str }
 *   GET  /audit/{job_id} → AuditStatusResponse (see below)
 *
 * AuditStatusResponse shape:
 * {
 *   job_id: str,
 *   status: "pending" | "indexing" | "auditing" | "complete" | "error",
 *   station: 1 | 2,
 *   log_lines: [ { station: 1|2, msg: str, level: "info"|"done"|"error" } ],
 *   final_status: "PASS" | "FAIL" | "REVIEW" | "ERROR" | null,
 *   final_report: { ... } | null,   // parsed JSON from audit_content_node
 *   error: str | null
 * }
 */

// ── Config ─────────────────────────────────────────────────────
const API_BASE     = "http://localhost:8000";   // adjust if your FastAPI runs elsewhere
const POLL_MS      = 2000;                       // status poll interval

// ── State ──────────────────────────────────────────────────────
let currentJobId   = null;
let pollTimer      = null;
let sevChart       = null;
let activeFilter   = "ALL";
let currentIssues  = [];

// ── Boot ───────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  checkBackend();
  document.getElementById("urlInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") startAudit();
  });
});

async function checkBackend() {
  try {
    const r = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (r.ok) setEnv("online", "Backend online");
    else      setEnv("offline", "Backend error");
  } catch {
    setEnv("offline", "Backend offline");
  }
}

function setEnv(state, label) {
  const dot = document.getElementById("envBadge").querySelector(".env-dot");
  const lbl = document.getElementById("envLabel");
  dot.className = "env-dot " + state;
  lbl.textContent = label;
}

// ── Example URLs ───────────────────────────────────────────────
function useExample(url) {
  document.getElementById("urlInput").value = url;
}

// ── Start audit ────────────────────────────────────────────────
async function startAudit() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) { flashInput(); return; }

  resetUI();
  setGlobalPill("running", "Running…");
  document.getElementById("auditBtn").disabled = true;
  document.getElementById("auditBtnText").textContent = "Running…";
  document.getElementById("emptyState").style.display = "none";
  document.getElementById("resultsSection").style.display = "none";

  try {
    const res = await fetch(`${API_BASE}/audit`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ video_url: url }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || "Failed to start audit");
    }

    const { job_id } = await res.json();
    currentJobId = job_id;
    pollTimer = setInterval(pollStatus, POLL_MS);
    pollStatus(); // immediate first poll

  } catch (err) {
    showError(`Could not reach backend: ${err.message}`);
  }
}

// ── Poll status ────────────────────────────────────────────────
async function pollStatus() {
  if (!currentJobId) return;

  try {
    const res = await fetch(`${API_BASE}/audit/${currentJobId}`);
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    applyStatus(data);
  } catch (err) {
    console.warn("[poll]", err.message);
  }
}

function applyStatus(data) {
  // Sync log lines from server
  syncLogs(data.log_lines || []);

  // Station visual states
  if (data.station === 1) {
    setStation(1, "active", "Indexing video…");
  }
  if (data.station === 2) {
    setStation(1, "done",   "Complete");
    setStation(2, "active", "Auditing content…");
  }

  if (data.status === "complete" || data.status === "error") {
    clearInterval(pollTimer);

    if (data.status === "error") {
      setStation(data.station || 1, "error", data.error || "Error");
      setGlobalPill("error", "Error");
      showError(data.error || "An error occurred");
      resetButton();
      return;
    }

    // Both stations done
    setStation(1, "done", "Complete");
    setStation(2, "done", "Complete");

    const status = data.final_status || "ERROR";
    setGlobalPill(
      status === "PASS" ? "pass" : status === "FAIL" ? "fail" : "review",
      status
    );

    renderResults(data.final_report, status);
    resetButton();
  }
}

// ── Log syncing ────────────────────────────────────────────────
const _renderedLogs = { 1: 0, 2: 0 };

function syncLogs(lines) {
  lines.forEach((line, idx) => {
    const station = line.station || 1;
    const logEl = document.getElementById(`log${station}`);
    if (idx < _renderedLogs[station]) return; // already rendered
    const div = document.createElement("div");
    const cls  = line.level === "done" ? "log-done" : line.level === "error" ? "log-err" : "log-active";
    div.className = `log-line ${cls}`;
    div.textContent = line.msg;
    logEl.appendChild(div);
    _renderedLogs[station]++;
  });
}

// ── Render results ─────────────────────────────────────────────
function renderResults(report, finalStatus) {
  if (!report) return;

  const issues  = report.issues || [];
  const summary = report.summary || "";
  const meta    = report.video   || {};
  currentIssues = issues;

  // Verdict banner
  const verdictEl  = document.getElementById("verdictBanner");
  const vcls = finalStatus === "PASS" ? "verdict-pass" : finalStatus === "FAIL" ? "verdict-fail" : "verdict-review";
  verdictEl.className = `verdict-banner ${vcls}`;
  verdictEl.innerHTML = `
    <div class="verdict-left">
      <div class="vl-label">Final Verdict</div>
      <div class="vl-status">${finalStatus}</div>
    </div>
    <div class="verdict-summary">${summary}</div>
  `;

  // Metrics
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  issues.forEach(i => { counts[i.severity] = (counts[i.severity] || 0) + 1; });

  document.getElementById("metricsGrid").innerHTML = [
    { label: "Total Issues",    val: issues.length,      cls: "" },
    { label: "Critical",        val: counts.CRITICAL,    cls: counts.CRITICAL > 0 ? "c-fail"   : "" },
    { label: "High",            val: counts.HIGH,        cls: counts.HIGH     > 0 ? "c-review" : "" },
    { label: "Med / Low",       val: counts.MEDIUM + counts.LOW, cls: "" },
  ].map(m => `
    <div class="metric">
      <div class="metric-label">${m.label}</div>
      <div class="metric-val ${m.cls}">${m.val}</div>
    </div>
  `).join("");

  // Filter buttons
  const filterSevs = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
  document.getElementById("filterRow").innerHTML = filterSevs.map(s => `
    <button class="filter-btn ${s === activeFilter ? 'active-filter' : ''}"
            onclick="setFilter('${s}')">${s}</button>
  `).join("");

  // Issues table
  renderIssuesTable(issues);

  // Chart
  renderChart(counts);

  // Metadata
  const metaItems = [
    ["Title",    meta.title || report.video_metadata?.title || "—"],
    ["Channel",  meta.channel || report.video_metadata?.channel || "—"],
    ["Duration", meta.duration || report.video_metadata?.duration || "—"],
    ["Views",    meta.view_count || report.video_metadata?.view_count || "—"],
    ["Date",     meta.upload_date || report.video_metadata?.upload_date || "—"],
  ];
  document.getElementById("metaBlock").innerHTML = metaItems.map(([k, v]) => `
    <div class="meta-row">
      <span class="meta-key">${k}</span>
      <span class="meta-val" title="${v}">${v}</span>
    </div>
  `).join("");

  document.getElementById("resultsSection").style.display = "block";
}

function renderIssuesTable(issues) {
  const filtered = activeFilter === "ALL"
    ? issues
    : issues.filter(i => i.severity === activeFilter);

  const tbody = document.getElementById("issuesTbody");
  const none  = document.getElementById("noIssues");

  if (filtered.length === 0) {
    tbody.innerHTML = "";
    none.style.display = "flex";
    return;
  }
  none.style.display = "none";

  tbody.innerHTML = filtered.map((iss, idx) => {
    const sev  = (iss.severity || "LOW").toUpperCase();
    const scls = `sev-${sev.toLowerCase()}`;
    return `
      <tr onclick="openIssueModal(${idx})">
        <td>
          <span class="sev ${scls}">
            <span class="sev-dot"></span>${sev}
          </span>
        </td>
        <td style="color:var(--text2);font-size:11px;">${iss.category || "—"}</td>
        <td>${iss.description || "—"}</td>
        <td style="font-family:var(--font-mono);color:var(--text3);white-space:nowrap;">${iss.timestamp || "—"}</td>
        <td><button class="expand-btn">↗</button></td>
      </tr>
    `;
  }).join("");
}

function renderChart(counts) {
  const palette = {
    CRITICAL: "#e8564a",
    HIGH:     "#e8a230",
    MEDIUM:   "#d4c040",
    LOW:      "#6c8fff",
  };
  const labels = Object.keys(counts);
  const data   = labels.map(k => counts[k]);
  const colors = labels.map(k => palette[k]);
  const total  = data.reduce((a, b) => a + b, 0);

  document.getElementById("chartLegend").innerHTML = labels.map(k => `
    <span class="legend-item">
      <span class="legend-swatch" style="background:${palette[k]}"></span>
      ${k} ${counts[k]}
    </span>
  `).join("");

  document.getElementById("chartCenter").innerHTML = `
    <div class="chart-center-num">${total}</div>
    <div class="chart-center-sub">Issues</div>
  `;

  if (sevChart) sevChart.destroy();

  const ctx = document.getElementById("sevChart");
  sevChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 0,
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "68%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.raw}`,
          },
        },
      },
    },
  });
}

// ── Filter ─────────────────────────────────────────────────────
function setFilter(sev) {
  activeFilter = sev;
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.classList.toggle("active-filter", btn.textContent === sev);
  });
  renderIssuesTable(currentIssues);
}

// ── Issue modal ────────────────────────────────────────────────
function openIssueModal(idx) {
  const issues  = activeFilter === "ALL"
    ? currentIssues
    : currentIssues.filter(i => i.severity === activeFilter);
  const iss = issues[idx];
  if (!iss) return;

  const sev  = (iss.severity || "LOW").toUpperCase();
  const scls = `sev-${sev.toLowerCase()}`;

  document.getElementById("modalContent").innerHTML = `
    <div class="modal-sev-row">
      <span class="sev ${scls}"><span class="sev-dot"></span>${sev}</span>
      <span class="modal-category">${iss.category || ""}</span>
    </div>
    <div class="modal-desc">${iss.description || ""}</div>
    ${iss.evidence ? `
      <div class="modal-evidence-label">Evidence from content</div>
      <div class="modal-evidence">${iss.evidence}</div>
    ` : ""}
    ${iss.rule_id ? `<div class="modal-rule-id">Rule: ${iss.rule_id}</div>` : ""}
    ${iss.timestamp ? `<div class="modal-rule-id" style="margin-top:4px;">Timestamp: ${iss.timestamp}</div>` : ""}
  `;
  document.getElementById("issueModal").style.display = "flex";
}

function closeModal(e) {
  if (e.target === document.getElementById("issueModal")) {
    document.getElementById("issueModal").style.display = "none";
  }
}

// ── Helpers ────────────────────────────────────────────────────
function setStation(num, state, text) {
  document.getElementById(`station${num}`).className = `station ${state}`;
  document.getElementById(`dot${num}`).className = `station-dot ${state}`;
  document.getElementById(`s${num}text`).textContent = text;
}

function setGlobalPill(state, label) {
  const el = document.getElementById("globalStatus");
  el.className = `status-pill pill-${state}`;
  el.textContent = label;
}

function resetButton() {
  const btn = document.getElementById("auditBtn");
  btn.disabled = false;
  document.getElementById("auditBtnText").textContent = "Run Audit";
}

function showError(msg) {
  document.getElementById("emptyState").style.display = "flex";
  document.getElementById("emptyState").querySelector(".empty-sub").textContent = `Error: ${msg}`;
  document.getElementById("emptyState").querySelector(".empty-title").textContent = "Audit failed";
}

function flashInput() {
  const el = document.querySelector(".url-bar");
  el.style.borderColor = "var(--fail)";
  setTimeout(() => { el.style.borderColor = ""; }, 800);
}

function resetUI() {
  _renderedLogs[1] = 0;
  _renderedLogs[2] = 0;
  document.getElementById("log1").innerHTML = "";
  document.getElementById("log2").innerHTML = "";
  [1, 2].forEach(n => setStation(n, "", "Waiting"));
  setGlobalPill("idle", "Idle");
  currentIssues = [];
  activeFilter  = "ALL";
  if (sevChart) { sevChart.destroy(); sevChart = null; }
}

// ── Chart.js ───────────────────────────────────────────────────
// Loaded via CDN tag in index.html — add this before </body>:
// <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>