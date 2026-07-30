"use strict";

/* Job Radar dashboard.
   Application state (applied / dismissed) lives in localStorage and is never
   sent anywhere. The repository is public; a job hunt is not. */

const LS = "jobradar-state-v1";
const state = { jobs: [], run: null, mark: {}, f: { band: "all", geo: "all", sen: "all", q: "", hide: true }, sort: "score" };

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- theme ---------- */
(function theme() {
  const K = "jobradar-theme";
  const saved = localStorage.getItem(K);
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  const sun = '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  const moon = '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"/></svg>';
  const dark = () => { const t = document.documentElement.getAttribute("data-theme"); return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches; };
  const paint = () => { const b = $(".theme-toggle"); if (b) { b.innerHTML = dark() ? sun : moon; b.setAttribute("aria-label", dark() ? "Switch to light mode" : "Switch to dark mode"); } };
  window.toggleTheme = () => { document.documentElement.setAttribute("data-theme", dark() ? "light" : "dark"); localStorage.setItem(K, document.documentElement.getAttribute("data-theme")); paint(); };
  document.addEventListener("DOMContentLoaded", paint);
})();

/* ---------- persistence ---------- */
function loadMarks() { try { state.mark = JSON.parse(localStorage.getItem(LS) || "{}"); } catch { state.mark = {}; } }
function saveMarks() { localStorage.setItem(LS, JSON.stringify(state.mark)); }

/* ---------- rendering ---------- */
const BAND_CLASS = { strong: "strong", "worth a look": "look", stretch: "stretch" };
const GEO_LABEL = {
  apac: ["Indonesia / APAC", "apac"],
  worldwide: ["Open worldwide", "apac"],
  "remote-unspecified": ["Remote, region unstated", ""],
  elsewhere: ["Needs relocation + visa", "warn"],
  unknown: ["Location unstated", ""],
  restricted: ["Blocked", "bad"],
};

function visible() {
  const f = state.f;
  const q = f.q.trim().toLowerCase();
  return state.jobs.filter((j) => {
    if (f.hide && (state.mark[j.id] === "applied" || state.mark[j.id] === "hidden")) return false;
    if (f.band !== "all" && j.b !== f.band) return false;
    if (f.geo !== "all" && j.geo !== f.geo) return false;
    if (f.sen !== "all" && j.sen !== f.sen) return false;
    if (q && !(`${j.t} ${j.c} ${j.l} ${(j.m || []).join(" ")}`.toLowerCase().includes(q))) return false;
    return true;
  }).sort((a, b) => (state.sort === "score" ? b.sc - a.sc : String(b.d).localeCompare(String(a.d))));
}

function row(j) {
  const mark = state.mark[j.id];
  const [geoText, geoCls] = GEO_LABEL[j.geo] || ["", ""];
  const senBad = ["senior", "staff", "principal", "management"].includes(j.sen);
  return `
  <article class="job ${mark ? "done" : ""}" data-id="${j.id}">
    <div class="job-head">
      <div class="score ${BAND_CLASS[j.b] || "stretch"}">${j.sc}<small>FIT</small></div>
      <div class="job-main">
        <div class="job-title"><a href="${esc(j.u)}" target="_blank" rel="noopener noreferrer">${esc(j.t)}</a></div>
        <div class="job-sub"><span class="co">${esc(j.c)}</span> &middot; ${esc(j.l || "location unstated")}${j.d ? " &middot; " + esc(j.d) : ""}</div>
        <div class="badges">
          ${geoText ? `<span class="badge ${geoCls}">${geoText}</span>` : ""}
          <span class="badge ${senBad ? "warn" : ""}">${esc(j.sen)}</span>
          <span class="badge">${esc(j.r || "")}</span>
          <span class="badge">${esc(j.src)}</span>
          ${j.rx ? `<span class="badge bad">${esc(j.rx)}</span>` : ""}
        </div>
        <div class="why">${esc((j.why || []).join(" &middot; ")).replace(/&amp;middot;/g, "·")}</div>
        <div class="skills">
          ${(j.m || []).slice(0, 10).map((s) => `<span class="sk">${esc(s)}</span>`).join("")}
          ${(j.g || []).slice(0, 6).map((s) => `<span class="sk gap">${esc(s)} ?</span>`).join("")}
        </div>
        <div class="acts">
          <a class="btn primary" href="${esc(j.u)}" target="_blank" rel="noopener noreferrer">Open posting
            <svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M7 17L17 7M9 7h8v8"/></svg></a>
          <button class="btn ${mark === "applied" ? "on" : ""}" data-act="applied">${mark === "applied" ? "Applied" : "Mark applied"}</button>
          <button class="btn" data-act="hidden">${mark === "hidden" ? "Hidden" : "Not for me"}</button>
        </div>
      </div>
    </div>
  </article>`;
}

function render() {
  const rows = visible();
  $("#list").innerHTML = rows.length
    ? rows.map(row).join("")
    : `<div class="empty">Nothing matches these filters. Widen them, or clear the search.</div>`;
  $("#count").textContent = `${rows.length} shown of ${state.jobs.length}`;

  const applied = Object.values(state.mark).filter((v) => v === "applied").length;
  const hidden = Object.values(state.mark).filter((v) => v === "hidden").length;
  $("#applied").textContent = applied;
  $("#hidden-n").textContent = hidden;
}

/* ---------- wiring ---------- */
function wire() {
  $("#list").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const id = btn.closest(".job").dataset.id;
    const act = btn.dataset.act;
    state.mark[id] = state.mark[id] === act ? undefined : act;
    if (!state.mark[id]) delete state.mark[id];
    saveMarks(); render();
  });

  document.querySelectorAll("[data-filter]").forEach((el) => {
    el.addEventListener("change", () => { state.f[el.dataset.filter] = el.value; render(); });
  });
  $("#q").addEventListener("input", (e) => { state.f.q = e.target.value; render(); });
  $("#sort").addEventListener("change", (e) => { state.sort = e.target.value; render(); });
  $("#hide").addEventListener("click", (e) => {
    state.f.hide = !state.f.hide;
    e.target.setAttribute("aria-pressed", String(state.f.hide));
    e.target.textContent = state.f.hide ? "Hiding handled" : "Showing all";
    render();
  });
  $("#export").addEventListener("click", () => {
    const rows = state.jobs.filter((j) => state.mark[j.id] === "applied")
      .map((j) => [j.d, j.c, j.t, j.l, j.sc, j.u].join("\t"));
    const blob = new Blob(["date\tcompany\ttitle\tlocation\tfit\turl\n" + rows.join("\n")],
      { type: "text/tab-separated-values" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "applications.tsv";
    a.click();
  });
  $("#reset").addEventListener("click", () => {
    if (!confirm("Clear every applied and hidden mark on this device?")) return;
    state.mark = {}; saveMarks(); render();
  });
}

/* ---------- boot ---------- */
async function boot() {
  loadMarks();
  try {
    const [jobs, run] = await Promise.all([
      fetch("assets/jobs.json").then((r) => r.json()),
      fetch("assets/run.json").then((r) => r.json()),
    ]);
    state.jobs = jobs; state.run = run;
  } catch {
    $("#list").innerHTML = `<div class="empty">Could not load the job data. Reload the page.</div>`;
    return;
  }

  const r = state.run;
  $("#n-total").textContent = state.jobs.length;
  $("#n-strong").textContent = state.jobs.filter((j) => j.b === "strong").length;
  $("#n-apac").textContent = state.jobs.filter((j) => j.geo === "apac").length;
  $("#n-scanned").textContent = (r.deduped || 0).toLocaleString("en-GB");

  const gen = new Date(r.generated);
  const hours = (Date.now() - gen.getTime()) / 36e5;
  $("#gen").textContent = gen.toISOString().slice(0, 16).replace("T", " ") + " UTC";
  $("#age").textContent = hours < 1 ? "just now"
    : hours < 48 ? `${Math.round(hours)} h ago`
    : `${Math.round(hours / 24)} days ago`;
  if (hours > 60) $(".brand .dot").classList.add("stale");
  $("#failures").textContent = (r.failures || []).length;
  $("#boards").textContent = r.boards_probed || 0;

  wire();
  render();
}
document.addEventListener("DOMContentLoaded", boot);
