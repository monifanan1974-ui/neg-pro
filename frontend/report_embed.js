// frontend/report_embed.js
// Robust embed: finds or creates form/button/report-root so demo always works.

(function () {
  function onReady(fn){ if(document.readyState!=="loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }

  onReady(function(){
    // 1) Find a form (prefer #personaForm)
    let form = document.getElementById("personaForm") || document.querySelector("form[data-role='persona']") || document.querySelector("main form, form");
    // 2) Find or create report root
    let reportRoot = document.getElementById("report-root");
    if (!reportRoot) {
      reportRoot = document.createElement("div");
      reportRoot.id = "report-root";
      (form && form.parentNode ? form.parentNode : document.body).appendChild(reportRoot);
    }
    // 3) Find or create Build button
    let buildBtn = document.getElementById("buildBtn");
    if (!buildBtn) {
      buildBtn = document.createElement("button");
      buildBtn.type = "button";
      buildBtn.id = "buildBtn";
      buildBtn.textContent = "Build Presentation Report";
      buildBtn.style.cssText = "margin-top:12px;padding:.6rem 1rem;border-radius:10px;background:#0f172a;color:#fff;";
      if (form) form.appendChild(buildBtn); else document.body.insertBefore(buildBtn, reportRoot);
    }

    // If even a form is missing, bail gracefully
    if (!form) {
      console.warn("[report_embed] No form found. The script created a 'Build' button but has no fields to read.");
    }

    function val(name) {
      if (!form) return "";
      const el = form.elements[name];
      return el ? String(el.value || "").trim() : "";
    }

    function toList(csv) {
      if (!csv) return [];
      return csv.split(",").map(s => s.trim()).filter(Boolean);
    }

    function collectPayload() {
      const prioritiesCsv = val("priorities_ranked") || val("priorities");
      const answers = {
        industry: val("industry"),
        target_title: val("target_title"),
        role: val("target_title"),
        seniority: val("seniority"),
        country: val("country"),
        communication_style: val("communication_style"),
        counterpart_persona: val("counterpart_persona"),
        impacts: toList(val("achievements")),
        range_low: val("range_low") || val("salary_low") || "",
        range_high: val("range_high") || val("salary_high") || "",
        target_salary: val("target_salary") || val("anchor") || "",
        priorities_ranked: toList(prioritiesCsv),
        priorities: toList(prioritiesCsv),
        desired_tone: val("desired_tone")
      };
      return { answers, style: "html" };
    }

    function showLoading() {
      reportRoot.innerHTML = `
        <div class="rounded-xl" style="border:1px solid #e5e7eb;background:#fff;padding:12px;box-shadow:0 6px 18px rgba(2,6,23,.06)">
          <div style="font:14px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Arial;">Building report… 1–3 seconds.</div>
        </div>`;
    }

    function injectIframe(html) {
      reportRoot.innerHTML = "";
      const iframe = document.createElement("iframe");
      iframe.id = "report-frame";
      iframe.title = "Presentation Report";
      iframe.style.width = "100%";
      iframe.style.border = "0";
      iframe.style.minHeight = "1200px";
      reportRoot.appendChild(iframe);

      if ("srcdoc" in iframe) iframe.srcdoc = html;
      else {
        const doc = iframe.contentWindow.document;
        doc.open(); doc.write(html); doc.close();
      }
      setTimeout(() => {
        try {
          const h = iframe.contentWindow.document.documentElement.scrollHeight;
          if (h && h > 0) iframe.style.minHeight = Math.max(1000, h) + "px";
        } catch(_) {}
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
        if (!res.ok) throw new Error(`Server ${res.status}: ${await res.text()}`);
        const data = await res.json();
        if (!data || !data.html) throw new Error("Empty response from /report");
        injectIframe(data.html);
      } catch (err) {
        console.error("[report_embed] build failed:", err);
        alert("Failed to build report: " + (err && err.message ? err.message : "No engine endpoint responded."));
        reportRoot.innerHTML = "";
      }
    }

    buildBtn.addEventListener("click", buildReport);
  });
})();
