// frontend/report_embed.js
<<<<<<< HEAD
document.addEventListener("DOMContentLoaded", () => {
    console.log("📄 report_embed.js loaded");

    const payloadPreview = document.querySelector("#payload-preview");
    const reportContainer = document.querySelector("#report-container");
    const nextBtn = document.querySelector("#next-btn");
    const backBtn = document.querySelector("#back-btn");
    const buildReportBtn = document.querySelector("#build-report-btn");
    const prefillBtn = document.querySelector("#prefill-btn");
    const resetBtn = document.querySelector("#reset-btn");

    let questionnaire = [];
    let currentStep = 0;
    let answers = {};

    // === Load questionnaire ===
    async function loadQuestionnaire() {
        try {
            const res = await fetch("/frontend/questionnaire.json");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            questionnaire = await res.json();
            console.log("✅ Questionnaire loaded", questionnaire);
            showStep(0);
        } catch (err) {
            console.error("❌ Failed to load questionnaire:", err);
        }
    }

    // === Show a step ===
    function showStep(index) {
        currentStep = index;
        const stepData = questionnaire[index];
        if (!stepData) {
            console.warn("No step data for index", index);
            return;
        }
        document.querySelector("#step-title").textContent = stepData.title || `Step ${index + 1}`;
        document.querySelector("#step-description").textContent = stepData.description || "";
        renderInputs(stepData);
        updatePayloadPreview();
    }

    // === Render inputs ===
    function renderInputs(stepData) {
        const container = document.querySelector("#step-content");
        container.innerHTML = "";
        (stepData.questions || []).forEach(q => {
            const input = document.createElement("input");
            input.type = "text";
            input.placeholder = q.text;
            input.value = answers[q.id] || "";
            input.addEventListener("input", e => {
                answers[q.id] = e.target.value;
                updatePayloadPreview();
            });
            container.appendChild(input);
        });
    }

    // === Update payload preview ===
    function updatePayloadPreview() {
        if (payloadPreview) {
            payloadPreview.value = JSON.stringify({ answers }, null, 2);
        }
    }

    // === Navigation buttons ===
    nextBtn?.addEventListener("click", () => {
        if (currentStep < questionnaire.length - 1) {
            showStep(currentStep + 1);
        }
    });

    backBtn?.addEventListener("click", () => {
        if (currentStep > 0) {
            showStep(currentStep - 1);
        }
    });

    prefillBtn?.addEventListener("click", () => {
        questionnaire.forEach(step => {
            (step.questions || []).forEach(q => {
                answers[q.id] = "Sample answer";
            });
        });
        updatePayloadPreview();
    });

    resetBtn?.addEventListener("click", () => {
        answers = {};
        showStep(0);
    });

    // === Build report ===
    buildReportBtn?.addEventListener("click", async () => {
        console.log("📤 Sending report request with answers:", answers);
        try {
            const res = await fetch("/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ answers, style: "html" })
            });

            const contentType = res.headers.get("content-type");
            if (contentType && contentType.includes("application/json")) {
                const data = await res.json();
                reportContainer.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
            } else {
                const html = await res.text();
                reportContainer.innerHTML = html;
            }
        } catch (err) {
            console.error("❌ Failed to get report:", err);
            reportContainer.innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
        }
    });

    // Init
    loadQuestionnaire();
});
=======
// Connects form -> /questionnaire/report and renders a report (iframe or inline).
// Injects a tiny RTL/CSS fix for the mini-form segment without touching index.html.

(function(){
  const form = document.getElementById('np-form');
  const statusEl = document.getElementById('np-status');
  const root = document.getElementById('report-root');

  let lastReportId = null;
  let lastReportUrl = null;

  // --- Inject minimal CSS fix for the mini-form (keeps your theme intact)
  (function injectFixes(){
    const css = `
      #report-panel .np-row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
      #report-panel .np-field label{display:block;font-weight:600;margin-bottom:.35rem}
      #report-panel input, #report-panel select{
        width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);
        background:#0B101A;color:#E7ECF7;outline:none;direction:rtl;text-align:right;
      }
      @media (max-width: 920px){ #report-panel .np-row{grid-template-columns:1fr} }
      /* keep button pinned nicely on mobile */
      #report-panel .np-btn{margin-top:.5rem}
    `;
    const tag = document.createElement('style');
    tag.setAttribute('data-np-fix','rtl');
    tag.textContent = css;
    document.head.appendChild(tag);
  })();

  function setStatus(msg, type){
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.className = 'np-status' + (type ? ' ' + type : '');
  }

  function toPayload(f){
    if (!f) return {};
    const fd = new FormData(f), obj = {};
    fd.forEach((v,k)=>obj[k]=v);

    ['priorities','impact'].forEach(k=>{
      if (typeof obj[k] === 'string' && obj[k].trim()){
        obj[k] = obj[k].split(',').map(x=>x.trim()).filter(Boolean);
      }
    });

    ['salary_low','salary_high','salary_target'].forEach(k=>{
      const n = Number(obj[k]);
      if (!Number.isNaN(n)) obj[k] = n;
    });
    return obj;
  }

  async function postJSON(url, data){
    const res = await fetch(url, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    const isJSON = (res.headers.get('content-type')||'').includes('application/json');
    if (!res.ok){
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    return isJSON ? res.json() : {};
  }

  function renderReportFromResponse(data){
    lastReportId = data.report_id || null;
    lastReportUrl = data.report_url || null;

    if (data.html_output){
      root.innerHTML = data.html_output;
    } else if (data.report_url){
      const iframe = document.createElement('iframe');
      iframe.src = data.report_url;
      iframe.title = 'Negotiation Report';
      iframe.style.width = '100%';
      iframe.style.minHeight = '640px';
      iframe.style.border = 'none';
      root.innerHTML = '';
      root.appendChild(iframe);
    } else {
      root.innerHTML = '<p>No report content returned.</p>';
    }
    root.scrollIntoView({behavior:'smooth'});
  }

  async function handleSubmit(e){
    e.preventDefault();
    setStatus('Generating...', '');
    root?.classList.add('np-loading');
    try{
      const data = await postJSON('/questionnaire/report', toPayload(form));
      if (!data.ok && !data.report_url && !data.html_output) throw new Error(data.error || 'Unknown error');

      renderReportFromResponse(data);
      setStatus('Done ✓','ok');
    }catch(err){
      console.error(err);
      setStatus('Error: ' + err.message, 'err');
      if (root && !root.innerHTML.trim()) root.innerHTML = '<p>No report rendered.</p>';
    }finally{
      root?.classList.remove('np-loading');
    }
  }

  if (form) form.addEventListener('submit', handleSubmit);

  // Expose helper API for the SPA stepper
  window.NP_Report = {
    async render(answers){
      setStatus('Generating...', '');
      root?.classList.add('np-loading');
      try{
        const data = await postJSON('/questionnaire/report', { answers });
        if (!data.ok && !data.report_url && !data.html_output) throw new Error(data.error || 'Unknown error');
        renderReportFromResponse(data);
        setStatus('Done ✓','ok');
      }catch(e){
        console.error(e);
        setStatus('Error: ' + e.message, 'err');
      }finally{
        root?.classList.remove('np-loading');
      }
    },
    async downloadPDF(){
      if (lastReportId){
        try{
          const res = await fetch(`/report/${lastReportId}.pdf`);
          if (res.ok && res.headers.get('content-type')?.includes('application/pdf')){
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `negotiation_report_${lastReportId}.pdf`; a.click();
            URL.revokeObjectURL(url);
            return;
          }
          if (res.headers.get('content-type')?.includes('application/json')){
            const j = await res.json();
            console.warn('PDF not available:', j);
          }
        }catch(e){ console.warn('PDF download failed, falling back to HTML:', e); }
      }
      // Fallback: download current HTML
      let content = '';
      const iframe = root.querySelector('iframe');
      if (iframe && iframe.contentDocument){
        content = iframe.contentDocument.documentElement.outerHTML;
      } else {
        content = root.innerHTML;
      }
      const blob = new Blob([content], {type:'text/html'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'negotiation_report.html'; a.click();
      URL.revokeObjectURL(url);
    },
    async saveToProfile(){
      if (!lastReportId){ alert('No report to save yet.'); return; }
      try{
        const res = await postJSON('/reports/save', {
          report_id: lastReportId,
          title: 'Negotiation Report',
          tags: ['strategy','report']
        });
        if (!res.ok && !res.saved_path) throw new Error(res.error || 'Save failed');
        alert('Saved ✓');
      }catch(e){
        console.error(e);
        alert('Save failed: ' + e.message);
      }
    }
  };
})();
>>>>>>> 761b083 (Your commit message here)
