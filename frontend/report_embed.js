// Simple helper: read/write
const $ = (id) => document.getElementById(id);
const LS_KEY = "negpro_answers_v1";

function readForm() {
  return {
    answers: {
      role: $("role").value.trim(),
      target_title: $("role").value.trim(),
      seniority: $("seniority").value,
      country: $("country").value.trim() || "UK",
      industry: $("industry").value.trim(),
      communication_style: $("communication_style").value.trim(),
      counterpart_persona: $("counterpart_persona").value.trim(),
      range_low: $("range_low").value.trim(),
      range_high: $("range_high").value.trim(),
      target_salary: $("target_salary").value.trim(),
      market_sources: $("market_sources").value.split(",").map(s => s.trim()).filter(Boolean)
    },
    style: "html"
  };
}

function writePreview(payload) {
  $("preview").textContent = JSON.stringify(payload, null, 2);
  try { localStorage.setItem(LS_KEY, JSON.stringify(payload)); } catch {}
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw) || {};
    const a = saved.answers || {};
    $("role").value = a.role || a.target_title || "";
    $("seniority").value = a.seniority || "mid";
    $("country").value = a.country || "UK";
    $("industry").value = a.industry || "";
    $("communication_style").value = a.communication_style || "";
    $("counterpart_persona").value = a.counterpart_persona || "";
    $("range_low").value = a.range_low || "";
    $("range_high").value = a.range_high || "";
    $("target_salary").value = a.target_salary || "";
    $("market_sources").value = (a.market_sources || []).join(", ");
  } catch {}
}

async function buildReport() {
  const payload = readForm();
  writePreview(payload);

  $("status").textContent = "Building…";
  $("status").className = "hint";

  try {
    // IMPORTANT: our backend expects POST /report with { answers:{...}, style:"html" }
    const res = await fetch("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const txt = await res.text();
      $("status").innerHTML = `❌ <span class="err">Error ${res.status}</span>`;
      console.error("Report error:", txt);
      return;
    }

    const data = await res.json();
    const html = data && data.html ? data.html : "<h1>Empty report</h1>";

    // write into iframe
    const iframe = $("report");
    const doc = iframe.contentDocument || iframe.contentWindow.document;
    doc.open();
    doc.write(html);
    doc.close();

    $("status").innerHTML = `✅ <span class="ok">OK</span>`;
  } catch (e) {
    $("status").innerHTML = `❌ <span class="err">${e.message}</span>`;
    console.error(e);
  }
}

function bind() {
  loadFromStorage();
  writePreview(readForm());

  // live preview
  document.querySelectorAll("input,select,textarea").forEach(el => {
    el.addEventListener("input", () => writePreview(readForm()));
    el.addEventListener("change", () => writePreview(readForm()));
  });

  $("btn-build").addEventListener("click", (e) => {
    e.preventDefault();
    buildReport();
  });

  $("btn-reset").addEventListener("click", (e) => {
    e.preventDefault();
    localStorage.removeItem(LS_KEY);
    document.querySelectorAll("input").forEach(i => i.value = "");
    $("seniority").value = "mid";
    $("country").value = "UK";
    $("market_sources").value = "Glassdoor, Levels.fyi";
    writePreview(readForm());
    $("report").src = "about:blank";
    $("status").textContent = "";
  });
}

window.addEventListener("DOMContentLoaded", bind);
