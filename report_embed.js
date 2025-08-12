// frontend/report_embed.js
// Multi-step questionnaire → POST /questionnaire/report → display HTML in an iframe.
// All comments and UI strings are in English only.

(function () {
  const LS_KEY = "np_qn_answers_v1";
  const LS_STEP = "np_qn_step_v1";

  const el = (t, a = {}, ...kids) => {
    const e = document.createElement(t);
    Object.entries(a).forEach(([k, v]) => {
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else e.setAttribute(k, v);
    });
    kids.flat().forEach(k => {
      if (k == null) return;
      if (typeof k === "string") e.appendChild(document.createTextNode(k));
      else e.appendChild(k);
    });
    return e;
  };

  const form = document.getElementById("qnForm");
  const stepsEl = document.getElementById("steps");
  const barEl = document.getElementById("bar");
  const statusEl = document.getElementById("status");
  const backBtn = document.getElementById("back");
  const nextBtn = document.getElementById("next");
  const buildBtn = document.getElementById("build");
  const payloadTA = document.getElementById("payload");
  const reportIF = document.getElementById("report");
  const prefillBtn = document.getElementById("prefill");
  const resetBtn = document.getElementById("reset");
  const toast = document.getElementById("toast");

  let spec = null, phases = [], step = 0, answers = {};

  const showToast = (m) => {
    toast.textContent = m;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 1200);
  };
  const saveLocal = () => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(answers));
      localStorage.setItem(LS_STEP, String(step));
    } catch {}
  };
  const loadLocal = () => {
    try {
      const a = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
      const s = parseInt(localStorage.getItem(LS_STEP) || "0", 10);
      if (a && typeof a === "object") answers = a;
      if (!Number.isNaN(s)) step = s;
    } catch {}
  };

  const numify = (k, v) => {
    if (/salary|bonus|percent/i.test(k)) {
      const n = String(v).replace(/[£,\s]/g, "").replace(/k$/i, "000");
      return n ? Number(n) : v;
    }
    if (/rating/i.test(k)) return v ? Number(v) : v;
    return v;
  };
  const coerceList = (v) => Array.isArray(v) ? v : (v ? [v] : []);

  const visibleIf = (expr, a) => {
    if (!expr) return true;
    try {
      const includes = (arr, val) => (Array.isArray(arr) ? arr.includes(val) : false);
      if (!/^[\w\s\.\(\)><=!\|\&,'"]+$/.test(expr)) return true;
      // eslint-disable-next-line no-new-func
      const fn = new Function("answers", "includes", `return (${expr});`);
      return !!fn(a, includes);
    } catch { return true; }
  };

  const renderStepsBar = () => {
    stepsEl.innerHTML = "";
    phases.forEach((_, i) => stepsEl.appendChild(el("div", { class: "dot" + (i === step ? " active" : "") })));
    const pct = Math.round(((step) / Math.max(1, phases.length - 1)) * 100);
    barEl.style.width = `${pct}%`;
  };
  const putPayload = () => payloadTA.value = JSON.stringify({ questionnaire: answers }, null, 2);

  const renderQuestion = (q) => {
    const block = el("div", { class: "q", "data-qid": q.id });
    const label = el("label", {}, q.question || q.id);
    if (q.help) label.appendChild(el("span", { class: "note", style: "margin-left:6px" }, q.help));
    block.appendChild(label);

    const t = (q.answerType || "").toLowerCase();
    const name = q.id;
    const opts = Array.isArray(q.options) ? q.options : [];
    const val = answers[name];

    const E = {
      single_choice: () => {
        opts.forEach((o, i) => {
          const v = (o.value != null ? o.value : o.label);
          const line = el("div", { class: "opt" },
            el("input", { type: "radio", name, value: String(v), id: `${name}_${i}`, checked: String(val) === String(v) ? "" : null }),
            el("label", { for: `${name}_${i}` }, o.label || String(v))
          );
          block.appendChild(line);
        });
      },
      multiple_choice: () => {
        const current = coerceList(val);
        opts.forEach((o, i) => {
          const v = (o.value != null ? o.value : o.label);
          const checked = current.includes(String(v)) ? "" : null;
          const line = el("div", { class: "opt" },
            el("input", { type: "checkbox", name, value: String(v), id: `${name}_${i}`, checked }),
            el("label", { for: `${name}_${i}` }, o.label || String(v))
          );
          block.appendChild(line);
        });
      },
      rating_scale: () => {
        const sel = el("select", { name });
        [1, 2, 3, 4, 5].forEach(v => sel.appendChild(el("option", { value: String(v), selected: String(val) === String(v) ? "" : null }, String(v))));
        block.appendChild(sel);
      },
      likert_scale_group: () => {
        (q.options || []).forEach((o, i) => {
          const sub = `${name}__${o.value || i}`;
          const cur = (answers[name] || {})[o.value || i];
          const row = el("div", { class: "row" },
            el("span", { class: "note" }, o.label || `Item ${i + 1}`),
            (function () {
              const sel = el("select", { name: sub });
              [1, 2, 3, 4, 5].forEach(v => sel.appendChild(el("option", { value: String(v), selected: String(cur) === String(v) ? "" : null }, String(v))));
              return sel;
            })()
          );
          block.appendChild(row);
        });
      },
      free_text_limited: () => {
        const ta = el("textarea", { name, rows: q.rows ? String(q.rows) : "3", placeholder: q.placeholder || "" }, "");
        if (val != null) ta.value = String(val);
        const counter = el("div", { class: "note", id: `${name}__counter` }, "");
        ta.addEventListener("input", () => {
          const max = q.max_chars || 400;
          counter.textContent = `${ta.value.length}/${max}`;
          if (ta.value.length > max) counter.classList.add("error"); else counter.classList.remove("error");
        });
        ta.dispatchEvent(new Event("input"));
        block.appendChild(ta); block.appendChild(counter);
      }
    };
    if (E[t]) E[t](); else {
      const inp = el("input", { type: "text", name, placeholder: q.placeholder || name });
      if (val != null) inp.value = String(val);
      block.appendChild(inp);
    }

    if (q.required) {
      block.appendChild(el("div", { class: "note" }, "Required"));
    }
    return block;
  };

  const collect = () => {
    const fd = new FormData(form);
    const out = {};
    const boxes = {};
    form.querySelectorAll('input[type=checkbox]').forEach(cb => {
      if (cb.checked) {
        boxes[cb.name] = boxes[cb.name] || [];
        boxes[cb.name].push(cb.value);
      } else {
        boxes[cb.name] = boxes[cb.name] || [];
      }
    });
    for (const [k, v] of fd.entries()) {
      if (form.querySelectorAll(`input[name="${k}"][type=checkbox]`).length) out[k] = boxes[k] || [];
      else if (form.querySelectorAll(`input[name="${k}"][type=radio]`).length) out[k] = v;
      else if (k.includes("__")) { /* likert handled below */ }
      else out[k] = numify(k, v);
    }
    const likerts = {};
    form.querySelectorAll('select[name*="__"]').forEach(sel => {
      const [id, sub] = sel.name.split("__");
      likerts[id] = likerts[id] || {};
      likerts[id][sub] = Number(sel.value);
    });
    Object.assign(out, likerts);
    return out;
  };

  const isVisible = (q) => visibleIf(q.visible_if, answers);

  const renderStep = () => {
    if (!phases.length) return;
    renderStepsBar();
    form.innerHTML = "";
    const ph = phases[step];
    (ph.questions || []).forEach(q => { if (isVisible(q)) form.appendChild(renderQuestion(q)); });
    backBtn.style.visibility = step === 0 ? "hidden" : "visible";
    nextBtn.style.display = (step < phases.length - 1) ? "inline-block" : "none";
    buildBtn.style.display = (step === phases.length - 1) ? "inline-block" : "none";
    statusEl.textContent = `Step ${step + 1} / ${phases.length}`;
    putPayload();
  };

  const go = (to) => {
    step = Math.max(0, Math.min(phases.length - 1, to));
    localStorage.setItem(LS_STEP, String(step));
    renderStep();
  };

  const buildReport = async () => {
    try {
      statusEl.textContent = "Building…";
      const res = await fetch("/questionnaire/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ questionnaire: answers }) });
      const data = await res.json();
      if (!data || !data.html) throw new Error(data && data.reason ? data.reason : "Empty response");
      if ("srcdoc" in reportIF) reportIF.srcdoc = String(data.html);
      else { const doc = reportIF.contentWindow.document; doc.open(); doc.write(String(data.html)); doc.close(); }
      statusEl.textContent = "Done ✓";
      showToast("Report ready");
    } catch (e) {
      console.error(e);
      statusEl.textContent = "Error: " + e.message;
      alert("Failed: " + e.message);
    }
  };

  (async function init(){
    try{
      // Load the questionnaire spec next to index.html (base URL is /app/)
      const resp = await fetch("questionnaire.json", { cache: "no-store" });
      if (!resp.ok) throw new Error("questionnaire.json not found next to index.html");
      spec = await resp.json();
      phases = spec.phases || [];
      loadLocal();
      renderStepsBar();
      renderStep();

      form.addEventListener("change", ()=>{ answers = collect(); putPayload(); saveLocal(); });
      form.addEventListener("input",  ()=>{ answers = collect(); putPayload(); saveLocal(); });

      backBtn.addEventListener("click", () => go(step - 1));
      nextBtn.addEventListener("click", () => go(step + 1));
      buildBtn.addEventListener("click", buildReport);

      prefillBtn.addEventListener("click", ()=>{
        const demo = {
          counterpart_style: "The Collaborator",
          counterpart_power: "peer",
          conflict_style: "Analytical",
          target_salary: "78000",
          key_benefits: ["remote_work","learning_budget"],
          culture_region: "UK",
          anxiety_rating: 3,
          prior_offer_status: "none",
          deadline_type: "firm",
          market_data_sources: ["Glassdoor","Levels.fyi"],
          current_challenges: ["budget_limitations"],
          main_leverage: ["Reduced edit cycle 28%","12/12 on-time campaigns"],
          target_title: "Senior Editor"
        };
        answers = Object.assign({}, answers, demo);
        renderStep();
        putPayload();
        showToast("Prefilled");
      });

      resetBtn.addEventListener("click", ()=>{
        answers = {};
        step = 0;
        localStorage.removeItem(LS_KEY);
        localStorage.removeItem(LS_STEP);
        renderStep();
        putPayload();
        showToast("Cleared");
      });
    } catch (e) {
      console.error(e);
      statusEl.textContent = "Failed to initialize: " + e.message;
    }
  })();
})();
