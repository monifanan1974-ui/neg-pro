// frontend/report_embed.js
// Collects form data -> POST /report -> injects returned HTML into an iframe.

(function () {
  const form = document.getElementById("personaForm");
  const buildBtn = document.getElementById("buildBtn");
  const reportRoot = document.getElementById("report-root");

  if (!form || !buildBtn || !reportRoot) {
    console.warn("[report_embed] Missing form/buildBtn/report-root in DOM.");
    return;
  }

  function val(name) {
    const el = form.elements[name];
    return el ? String(el.value || "").trim() : "";
  }

  function toList(v) {
    if (!v) return [];
    if (Array.isArray(v)) return v;
    return String(v).split(/[;,\n]/).map(s => s.trim()).filter(Boolean);
  }

  function collectPayload() {
    const prioritiesCsv = val("priorities_ranked") || val("priorities");
    const answers = {
      // Core mapping (mirrors questionnaire_mapper.py)
      industry: val("industry"),
      target_title: val("target_title"),
      role: val("target_title"), // alias for backward-compat
      seniority: val("seniority"),
      country: val("country"),

      communication_style: val("communication_style"),
      counterpart_persona: val("counterpart_persona"),

      // Achievements -> impacts (list)
      impacts: toList(val("achievements")),

      // Ranges / anchor (kept as strings; server can coerce if needed)
      range_low: val("range_low"),
      range_high: val("range_high"),
      target_salary: val("target_salary"),

      // Top priorities (Top-3)
      priorities_ranked: toList(prioritiesCsv),
      priorities: toList(prioritiesCsv),

      // Optional: tone
      desired_tone: val("desired_tone")
    };

    return { questionnaire: answers };
  }

  function showLoading() {
    reportRoot.innerHTML = "";
    const box = document.createElement("div");
    box.style.padding = "10px";
    box.style.color = "#9fb3d4";
    box.textContent = "Building report…";
    reportRoot.appendChild(box);
  }

  function injectIframe(html) {
    reportRoot.innerHTML = "";
    const iframe = document.createElement("iframe");
    iframe.setAttribute("sandbox", "allow-same-origin allow-forms allow-scripts");
    iframe.setAttribute("title", "NegotiationPro Report");
    iframe.style.width = "100%";
    iframe.style.border = "0";
    iframe.style.minHeight = "1200px";
    reportRoot.appendChild(iframe);

    if ("srcdoc" in iframe) {
      iframe.srcdoc = html;
    } else {
      const doc = iframe.contentWindow.document;
      doc.open();
      doc.write(html);
      doc.close();
    }
    // Auto-resize attempt
    setTimeout(() => {
      try {
        const h = iframe.contentWindow.document.documentElement.scrollHeight;
        if (h && h > 0) iframe.style.minHeight = Math.max(1000, h) + "px";
      } catch (_) {}
    }, 150);
  }

  async function buildReport() {
    try {
      showLoading();
      const payload = collectPayload();

      const res = await fetch("/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!data || !data.html) throw new Error("Empty response from /report");
      injectIframe(data.html);
    } catch (err) {
      console.error("[report_embed] build failed:", err);
      alert("Failed to build report: " + (err && err.message ? err.message : "Unknown error"));
      reportRoot.innerHTML = "";
    }
  }

  buildBtn.addEventListener("click", buildReport);
})();
