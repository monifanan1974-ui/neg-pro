// frontend/app.js — SPA logic

const API_BASE = ""; // Same-origin

/* ---------------- Templates ---------------- */
const Templates = {
  pageShell: (title, subtitle, content) => `
    <h1 class="page-title">${title}</h1>
    <p class="page-subtitle">${subtitle}</p>
    ${content}`,

  dashboard: (data) => {
    const kpiHtml = data.kpis.map(k => {
      if (k.type === "text") {
        return `
          <div class="card kpi-card elevate" data-aos="fade-up">
            <div class="kpi-value">${k.text}</div>
            <div class="kpi-label">${k.label}</div>
          </div>`;
      }
      const decimals = k.decimals ?? 0;
      const suffix = k.suffix ?? "";
      return `
        <div class="card kpi-card elevate" data-aos="fade-up">
          <div class="kpi-value" data-animate="count" data-end="${k.value}" data-decimals="${decimals}" data-suffix="${suffix}">0${suffix}</div>
          <div class="kpi-label">${k.label}</div>
        </div>`;
    }).join("");

    const skillsHtml = data.skills_breakdown.map(s => `
      <div class="skill-item" data-aos="fade-up">
        <div class="skill-label">${s.skill}</div>
        <div class="skill-bar"><span data-animate="bar" data-width="${s.score}"></span></div>
        <div class="skill-score">${s.score}%</div>
      </div>
    `).join("");

    return Templates.pageShell(
      "Dashboard",
      "A precise overview of your performance and negotiation skills.",
      `
      <div class="grid lg:grid-cols-4 gap-6">
        ${kpiHtml}
      </div>
      <div class="card elevate" data-aos="fade-up" style="margin-top:1.5rem">
        <h2 style="font-size:1.5rem;margin-bottom:.6rem">Negotiation skills</h2>
        <div class="skills-container">${skillsHtml}</div>
      </div>`
    );
  },

  strategy: () => Templates.pageShell(
    "Strategy Engine",
    "Answer the tailored questionnaire to get a deep strategy report.",
    `
    <div class="card stepper-container" data-aos="fade-up">
      <div id="strategy-stepper">
        <div class="text-center p-8"><p>Loading questionnaire...</p><div class="loading-spinner"></div></div>
      </div>
    </div>
    `
  ),

  practice: (scenarios) => Templates.pageShell(
    "Practice Scenarios",
    "Choose a scenario or run an AI drill to improve your skills.",
    `
    <div class="card" data-aos="fade-up" style="margin-bottom:1rem;">
      <div class="tabs" role="tablist" style="display:flex;gap:.5rem;flex-wrap:wrap;">
        <button class="btn secondary" data-tab="scenarios" aria-selected="true">Scenarios</button>
        <button class="btn secondary" data-tab="ai">AI Drill</button>
        <button class="btn secondary" data-tab="debrief">Debrief</button>
      </div>
    </div>

    <div id="tab-content">
      <div id="tab-scenarios">
        <div class="grid lg:grid-cols-3 gap-6">
          ${scenarios.map(s => `
            <div class="card practice-card" data-aos="fade-up">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
                  <h3 style="margin-bottom:0;">${s.title}</h3>
                  <span class="badge ${s.type === 'Hard' ? 'hard' : (s.type === 'Medium' ? 'medium' : 'easy')}">${s.type}</span>
                </div>
                <p style="color:var(--text-muted);font-size:.9rem;margin-bottom:1rem;">Skills: ${s.skills.join(", ")}</p>
              </div>
              <div>
                <div class="card-footer">
                  <span><i class="fa fa-clock" style="margin-left:.5rem;"></i>${s.duration}</span>
                  <span><i class="fa fa-users" style="margin-left:.5rem;"></i>${s.participants} participants</span>
                </div>
                <button class="btn start-practice" style="width:100%;margin-top:1rem;" data-title="${s.title}">Start practice</button>
              </div>
            </div>
          `).join("")}
        </div>
      </div>

      <div id="tab-ai" style="display:none">
        <div class="card chat-container" data-aos="fade-up">
          <div id="ai-drill-box">
            <div class="bubble ai">Hi! Let's run a short drill. State your goal in one sentence.</div>
          </div>
          <div class="chat-input-area">
            <input id="ai-drill-input" type="text" placeholder="Type your goal or question...">
            <button id="ai-drill-send" class="btn">Send</button>
          </div>
        </div>
      </div>

      <div id="tab-debrief" style="display:none">
        <div class="card" data-aos="fade-up">
          <h2>Debrief</h2>
          <p style="color:var(--text-muted)">Capture your takeaways after each drill or scenario.</p>
          <textarea id="debrief-notes" class="form-input" rows="5" placeholder="What worked? What will you try next time?"></textarea>
          <div style="margin-top:.75rem;display:flex;gap:.5rem;justify-content:flex-end;">
            <button id="save-debrief" class="btn">Save notes</button>
          </div>
        </div>
      </div>
    </div>
    `
  ),

  coach: () => Templates.pageShell(
    "AI Coach",
    "Chat with your negotiation coach for live tips and support.",
    `
    <div class="card chat-container" data-aos="fade-up">
      <div id="chat-box">
        <div class="bubble ai">Hi! I'm your negotiation coach. What's your goal for today's practice?</div>
      </div>
      <div class="chat-input-area">
        <input id="chat-input" type="text" placeholder="Type your question...">
        <button id="chat-send-btn" class="btn">Send</button>
      </div>
    </div>`
  ),

  analytics: (data) => Templates.pageShell(
    "Performance Analytics",
    "Track your progress and get tailored recommendations.",
    `
    <div class="grid md:grid-cols-2 gap-6">
      <div class="card" data-aos="fade-up">
        <h2>Recent results</h2>
        <div style="display:flex;flex-direction:column;gap:.75rem;">
          ${data.performance_scores.map(item => `
            <div class="kpi-list-item">
              <span>${item.label}</span>
              <span class="kpi-score">${item.score}</span>
            </div>
          `).join("")}
        </div>
      </div>
      <div class="card" data-aos="fade-up">
        <h2>Recommendations</h2>
        <div style="display:flex;flex-direction:column;gap:1rem;">
          ${data.improvement_suggestions.map(item => `
            <div class="suggestion-item">
              <h4 style="font-weight:700">${item.title}</h4>
              <p style="color:var(--text-muted);font-size:.9rem;">${item.description}</p>
            </div>
          `).join("")}
        </div>
      </div>
    </div>`
  ),

  settings: () => Templates.pageShell(
    "Settings",
    "Adjust your experience and preferences.",
    `
    <div class="card" style="max-width:800px;margin:auto;" data-aos="fade-up">
      <div class="setting-row">
        <div>
          <div style="font-weight:600;">Interface language</div>
          <div style="color:var(--text-muted);font-size:.9rem;">Currently set to English.</div>
        </div>
        <button class="btn secondary">Switch</button>
      </div>
      <div class="setting-row">
        <div>
          <div style="font-weight:600;">Notifications</div>
          <div style="color:var(--text-muted);font-size:.9rem;">Receive reminders and progress updates.</div>
        </div>
      </div>
    </div>`
  ),
};

/* ------------- Strategy Questionnaire ------------- */
let questionnaireSpec = null;
let currentPhaseIndex = 0;
let userAnswers = {};

async function loadQuestionnaire(){
  if (questionnaireSpec) return;
  try{
    const res = await fetch(`${API_BASE}/questionnaire/schema`);
    if(!res.ok) throw new Error(`Failed to load schema: ${res.statusText}`);
    questionnaireSpec = await res.json();
  }catch(e){
    console.error("Failed to load questionnaire:", e);
    const stepper = document.getElementById("strategy-stepper");
    if(stepper) stepper.innerHTML = `<p style="color:var(--color-bad);text-align:center;">Failed to load the questionnaire.</p>`;
  }
}

function renderStrategyStep(){
  const stepperContainer = document.getElementById("strategy-stepper");
  if(!stepperContainer || !questionnaireSpec) return;

  const phase = questionnaireSpec.phases[currentPhaseIndex];
  const progress = ((currentPhaseIndex + 1) / questionnaireSpec.phases.length) * 100;

  const questionsHTML = phase.questions.map(q => renderQuestion(q)).join("");

  stepperContainer.innerHTML = `
    <div class="progress-bar"><div class="progress-bar-inner" style="width:${progress}%"></div></div>
    <h2 class="question-title">${(phase.title || "").replace(/_/g, " ")}</h2>
    <p class="page-subtitle">${phase.description || ""}</p>
    <form id="questionnaire-form" style="display:flex;flex-direction:column;gap:1.5rem;">
      ${questionsHTML}
    </form>
    <div class="stepper-nav">
      <button id="strategy-back" class="btn secondary" ${currentPhaseIndex === 0 ? "disabled" : ""}>Back</button>
      <button id="strategy-next" class="btn">${currentPhaseIndex === questionnaireSpec.phases.length - 1 ? "Generate report" : "Next"}</button>
    </div>
  `;

  document.querySelectorAll(".choice-btn").forEach(label => {
    label.addEventListener("click", () => {
      const input = label.querySelector("input");
      if (input?.type === "radio") {
        document.querySelectorAll(`input[name="${input.name}"]`).forEach(radio => {
          radio.closest("label")?.classList.remove("selected");
        });
      }
      label.classList.toggle("selected", input?.checked);
    });
  });

  document.getElementById("strategy-back")?.addEventListener("click", () => {
    collectAnswers();
    if (currentPhaseIndex > 0) {
      currentPhaseIndex--;
      renderStrategyStep();
      refreshAOS();
    }
  });

  document.getElementById("strategy-next")?.addEventListener("click", (e) => {
    e.preventDefault();
    collectAnswers();
    if (currentPhaseIndex < questionnaireSpec.phases.length - 1) {
      currentPhaseIndex++;
      renderStrategyStep();
      refreshAOS();
    } else {
      finishStrategy();
    }
  });

  refreshAOS();
}

function renderQuestion(q){
  const currentValue = userAnswers[q.id];
  let inputHTML = "";

  switch (q.answerType) {
    case "single_choice":
      inputHTML = `<div class="choices-grid">${(q.options||[]).map(opt => `
        <label class="choice-btn ${currentValue === opt.value ? "selected" : ""}">
          <input type="radio" name="${q.id}" value="${opt.value}" ${currentValue === opt.value ? "checked" : ""}>
          ${opt.label}
        </label>`).join("")}</div>`;
      break;
    case "multiple_choice":
      inputHTML = `<div class="choices-grid">${(q.options||[]).map(opt => `
        <label class="choice-btn ${Array.isArray(currentValue) && currentValue.includes(opt.value) ? "selected" : ""}">
          <input type="checkbox" name="${q.id}" value="${opt.value}" ${Array.isArray(currentValue) && currentValue.includes(opt.value) ? "checked" : ""}>
          ${opt.label}
        </label>`).join("")}</div>`;
      break;
    case "free_text_limited":
      inputHTML = `<textarea name="${q.id}" rows="3" class="form-input" placeholder="${q.ui?.placeholder || ""}">${currentValue || ""}</textarea>`;
      break;
    case "rating_scale":
      inputHTML = `<input type="number" name="${q.id}" min="${q.scaleMin}" max="${q.scaleMax}" value="${currentValue || ""}" class="form-input" placeholder="Number between ${q.scaleMin} and ${q.scaleMax}">`;
      break;
    default:
      inputHTML = `<input type="text" name="${q.id}" value="${currentValue || ""}" class="form-input" placeholder="${q.ui?.placeholder || ""}">`;
  }

  return `<div data-aos="fade-up">
    <label style="font-weight:600;margin-bottom:.75rem;display:block;">${q.question}</label>
    ${inputHTML}
  </div>`;
}

function collectAnswers(){
  const form = document.getElementById("questionnaire-form");
  if(!form) return;
  const formData = new FormData(form);
  const names = new Set(Array.from(form.elements).map(el => el.name).filter(Boolean));

  names.forEach(key => {
    const allValues = formData.getAll(key);
    if (allValues.length > 1) userAnswers[key] = allValues;
    else if (allValues.length === 1) userAnswers[key] = allValues[0];
    else {
      const el = form.querySelector(`[name="${key}"]`);
      if (el && el.type === "checkbox") userAnswers[key] = [];
    }
  });
}

/** === Report popup control === */
function openReportModal(reportUrl){
  const modal = document.getElementById("report-modal");
  const iframe = document.getElementById("report-iframe");
  const closeBtn = document.getElementById("np-modal-close");
  const downloadBtn = document.getElementById("np-modal-download");
  const saveBtn = document.getElementById("np-modal-save");

  iframe.src = reportUrl;
  modal.style.display = "block";

  const onClose = () => { modal.style.display = "none"; iframe.src = "about:blank"; };
  closeBtn.onclick = onClose;
  modal.querySelector(".np-modal-backdrop").onclick = onClose;

  downloadBtn.onclick = () => {
    // prefer server-side PDF if route exists on same path (id embedded in URL)
    const m = /\/report\/([a-zA-Z0-9]+)$/.exec(reportUrl);
    if (m) {
      fetch(`/report/${m[1]}.pdf`).then(res => {
        if (res.ok && res.headers.get('content-type')?.includes('application/pdf')){
          return res.blob().then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = `negotiation_report_${m[1]}.pdf`; a.click();
            URL.revokeObjectURL(url);
          });
        } else {
          // fallback: open the HTML
          window.open(reportUrl, "_blank");
        }
      }).catch(()=> window.open(reportUrl, "_blank"));
    } else {
      window.open(reportUrl, "_blank");
    }
  };

  saveBtn.onclick = () => {
    const m = /\/report\/([a-zA-Z0-9]+)$/.exec(reportUrl);
    if (!m) return alert('No report id.');
    fetch('/reports/save', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ report_id: m[1], title: 'Negotiation Report', tags: ['strategy','report'] })
    }).then(r=>r.json()).then(j=>{
      if (j.ok) alert('Saved ✓'); else alert('Save failed');
    }).catch(()=>alert('Save failed'));
  };
}

async function finishStrategy(){
  const stepperContainer = document.getElementById("strategy-stepper");
  stepperContainer.innerHTML = `<div class="text-center p-8"><div class="loading-spinner"></div><p style="text-align:center;margin-top:1rem;">Generating your strategy report...</p></div>`;

  try{
    const response = await fetch(`${API_BASE}/questionnaire/report`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ answers: userAnswers })
    });
    if(!response.ok) throw new Error(`Server error: ${response.statusText}`);

    const data = await response.json();
    if (!data.ok && !data.report_url) throw new Error(data.reason || "Unknown error from server");

    // Popup modal with separate HTML (no inline form block anymore)
    stepperContainer.innerHTML = `<div class="card" style="text-align:center;padding:2rem;"><h3>Your report is ready</h3><p>Opening…</p></div>`;
    openReportModal(data.report_url);
  }catch(err){
    stepperContainer.innerHTML = `<div class="card text-center p-8" style="color:var(--color-bad);">Failed to generate report: ${err.message}</div>`;
  }
}

/* ------------- AI Coach ------------- */
async function sendChatMessage(){
  const chatInput = document.getElementById("chat-input");
  const chatBox = document.getElementById("chat-box");
  const message = chatInput.value.trim();
  if(!message) return;

  chatBox.insertAdjacentHTML("beforeend", `<div class="bubble me">${message}</div>`);
  chatInput.value = "";
  chatBox.scrollTop = chatBox.scrollHeight;

  const thinkingId = `thinking-${Date.now()}`;
  chatBox.insertAdjacentHTML("beforeend", `<div id="${thinkingId}" class="bubble ai"><span class="loading-spinner" style="width:20px;height:20px;margin:0;"></span></div>`);
  chatBox.scrollTop = chatBox.scrollHeight;

  try{
    const response = await fetch(`${API_BASE}/coach`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ msg: message })
    });
    const data = await response.json();
    const thinkingBubble = document.getElementById(thinkingId);
    if (thinkingBubble) thinkingBubble.textContent = data.reply;
  }catch(err){
    const thinkingBubble = document.getElementById(thinkingId);
    if (thinkingBubble) thinkingBubble.textContent = "Error. Try again later.";
  }
  chatBox.scrollTop = chatBox.scrollHeight;
}

/* ------------- Practice Tabs + AI Drill ------------- */
function initPracticeTabs(){
  const tabButtons = document.querySelectorAll('.tabs [data-tab]');
  const views = {
    scenarios: document.getElementById('tab-scenarios'),
    ai: document.getElementById('tab-ai'),
    debrief: document.getElementById('tab-debrief')
  };
  tabButtons.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      tabButtons.forEach(b=>b.setAttribute('aria-selected','false'));
      btn.setAttribute('aria-selected','true');
      const target = btn.dataset.tab;
      Object.entries(views).forEach(([k,el])=>{ el.style.display = (k===target)?'block':'none'; });
    });
  });

  // AI drill send
  const sendBtn = document.getElementById('ai-drill-send');
  const input = document.getElementById('ai-drill-input');
  const box = document.getElementById('ai-drill-box');
  function sendDrill(){
    const message = input.value.trim();
    if(!message) return;
    box.insertAdjacentHTML('beforeend', `<div class="bubble me">${message}</div>`);
    input.value = '';
    const thinkingId = `thinking-${Date.now()}`;
    box.insertAdjacentHTML('beforeend', `<div id="${thinkingId}" class="bubble ai"><span class="loading-spinner" style="width:20px;height:20px;margin:0;"></span></div>`);
    box.scrollTop = box.scrollHeight;

    fetch(`${API_BASE}/coach`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ msg: message })
    }).then(r=>r.json()).then(j=>{
      const t = document.getElementById(thinkingId);
      if (t) t.textContent = j.reply;
      box.scrollTop = box.scrollHeight;
    }).catch(()=>{
      const t = document.getElementById(thinkingId);
      if (t) t.textContent = 'Error. Try again later.';
    });
  }
  sendBtn?.addEventListener('click', sendDrill);
  input?.addEventListener('keypress', e=>{ if(e.key==='Enter') sendDrill(); });

  // Start practice buttons (from scenarios)
  document.querySelectorAll('.start-practice').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      // switch to AI tab and seed prompt
      document.querySelector('.tabs [data-tab="ai"]').click();
      const seed = `I want to practice: ${btn.dataset.title}. Give me a realistic prompt and a first move.`;
      input.value = seed;
    });
  });

  // Debrief save (local only stub)
  document.getElementById('save-debrief')?.addEventListener('click', ()=>{
    const notes = document.getElementById('debrief-notes').value.trim();
    if (!notes) return alert('Write a note first.');
    try{
      const all = JSON.parse(localStorage.getItem('np_debrief') || '[]');
      all.push({ ts: Date.now(), notes });
      localStorage.setItem('np_debrief', JSON.stringify(all));
      alert('Saved ✓');
    }catch{ alert('Save failed'); }
  });
}

/* ------------- Micro-animations (counters/bars) ------------- */
function animateOnView(){
  const root = document.getElementById("app-root");
  if(!root) return;

  const nums = [...root.querySelectorAll('[data-animate="count"]')];
  const bars = [...root.querySelectorAll('[data-animate="bar"]')];

  const io = new IntersectionObserver((entries)=>{
    entries.forEach(entry=>{
      if(!entry.isIntersecting) return;
      const el = entry.target;

      if (el.dataset.animate === "count"){
        const end = parseFloat(el.dataset.end || "0");
        const decimals = parseInt(el.dataset.decimals || "0", 10);
        const suffix = el.dataset.suffix || "";
        const start = 0;
        const dur = 900;
        const t0 = performance.now();
        function tick(t){
          const p = Math.min(1, (t - t0)/dur);
          const val = start + (end - start)*p;
          el.textContent = val.toFixed(decimals) + suffix;
          if (p<1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
        io.unobserve(el);
      }

      if (el.dataset.animate === "bar"){
        const w = parseInt(el.dataset.width || "0", 10);
        el.style.width = w + "%";
        io.unobserve(el);
      }
    });
  }, {threshold: .4});

  nums.forEach(n=>io.observe(n));
  bars.forEach(b=>io.observe(b));
}

/* ------------- AOS helpers ------------- */
function initAOS(){
  if (window.AOS && typeof window.AOS.init === "function"){
    window.AOS.init({ once: true, duration: 650, easing: "ease-out-cubic" });
  }
}
function refreshAOS(){
  if (window.AOS && typeof window.AOS.refreshHard === "function") window.AOS.refreshHard();
  else if (window.AOS && typeof window.AOS.refresh === "function") window.AOS.refresh();
}

/* ------------- SPA Router ------------- */
const app = {
  root: document.getElementById("app-root"),
  navLinks: document.querySelectorAll(".nav-link"),

  mockData: {
    dashboard: {
      kpis: [
        { label: "Total negotiations", value: 47, decimals: 0, suffix: "" },
        { label: "Success rate", value: 78, decimals: 0, suffix: "%" },
        { label: "Average score", value: 8.4, decimals: 1, suffix: "" },
        { label: "Skill level", type: "text", text: "Advanced" },
      ],
      skills_breakdown: [
        { skill: "Communication", score: 85 },
        { skill: "Strategy", score: 72 },
        { skill: "Analysis", score: 90 },
        { skill: "Creativity", score: 68 },
      ],
    },
    practice: [
      { title: "Salary negotiation", type: "Medium", skills: ["Confidence", "Value framing"], duration: "20–15 min", participants: 2 },
      { title: "Real-estate deal", type: "Hard", skills: ["Strategy", "Patience"], duration: "30–25 min", participants: 3 },
      { title: "Business agreement", type: "Easy", skills: ["Creativity", "Active listening"], duration: "15–10 min", participants: 2 },
    ],
    analytics: {
      performance_scores: [
        { label: "Salary negotiation", score: 9.2 },
        { label: "Real-estate deal", score: 7.8 },
        { label: "Business agreement", score: 8.9 },
      ],
      improvement_suggestions: [
        { title: "Use evidence-based arguments", description: "Bring quantifiable results and highlight impact." },
        { title: "Strengthen self-selling", description: "Write a strong opening and practice delivering it." },
      ]
    }
  },

  async loadPage(page){
    this.root.innerHTML = `<div class="loading-spinner"></div>`;
    try{
      switch(page){
        case "dashboard":
          this.root.innerHTML = Templates.dashboard(this.mockData.dashboard);
          animateOnView();
          refreshAOS();
          break;
        case "practice":
          this.root.innerHTML = Templates.practice(this.mockData.practice);
          initPracticeTabs();
          refreshAOS();
          break;
        case "analytics":
          this.root.innerHTML = Templates.analytics(this.mockData.analytics);
          refreshAOS();
          break;
        case "strategy":
          this.root.innerHTML = Templates.strategy();
          await loadQuestionnaire();
          renderStrategyStep();
          break;
        case "coach":
          this.root.innerHTML = Templates.coach();
          const btn = document.getElementById("chat-send-btn");
          const inp = document.getElementById("chat-input");
          btn?.addEventListener("click", sendChatMessage);
          inp?.addEventListener("keypress", (e)=>{ if(e.key==="Enter") sendChatMessage(); });
          refreshAOS();
          break;
        case "settings":
          this.root.innerHTML = Templates.settings();
          refreshAOS();
          break;
        default:
          this.root.innerHTML = `<div class="card">Not found.</div>`;
          refreshAOS();
      }
    }catch(e){
      this.root.innerHTML = `<div class="card" style="color:var(--color-bad);text-align:center">Failed to load page: ${e.message}</div>`;
    }
  },

  handleRouteChange(){
    const page = window.location.hash.substring(1) || "dashboard";
    this.navLinks.forEach(a => a.classList.toggle("active", a.dataset.target === page));
    this.loadPage(page);
  },

  init(){
    window.addEventListener("hashchange", ()=>this.handleRouteChange());
    initAOS();
    this.handleRouteChange();
  }
};

app.init();
