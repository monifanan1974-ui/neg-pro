/* frontend/app.js — SPA controller */
const API_BASE = ""; // same origin

// --------- Templates ---------
const Tpl = {
  shell(title, subtitle, inner) {
    return `
      <h1 class="page-title reveal">${title}</h1>
      <p class="page-sub reveal">${subtitle}</p>
      ${inner}
    `;
  },

  dashboard(data) {
    const kpis = `
      <section class="grid grid-4 reveal">
        ${data.kpis.map(k => `
          <div class="card kpi">
            <div class="val">${k.value}</div>
            <div class="lbl">${k.label}</div>
          </div>`).join("")}
      </section>
    `;

    const skills = `
      <section class="card reveal" style="margin-top:16px;">
        <h3 style="margin-bottom:12px;">Negotiation skills</h3>
        <div class="grid" style="gap:14px;">
          ${data.skills.map(s => `
            <div class="skill">
              <div class="name">${s.name}</div>
              <div class="track"><div class="fill" style="--w:${s.score}% ; width:${s.score}%"></div></div>
              <div class="pct">${s.score}%</div>
            </div>`).join("")}
        </div>
      </section>
    `;
    return Tpl.shell("Dashboard", "A precise overview of your performance and negotiation skills.", kpis + skills);
  },

  practice(items) {
    return Tpl.shell(
      "Practice Scenarios",
      "Choose a scenario to practice and improve your negotiation skills",
      `
      <section class="grid grid-3 reveal">
        ${items.map(s => `
          <div class="card" style="display:flex; flex-direction:column; gap:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <h3>${s.title}</h3>
              <span class="badge ${s.badgeCls}">${s.level}</span>
            </div>
            <div style="color:var(--muted); font-size:.95rem;">Skills: ${s.skills.join(", ")}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; color:var(--text-1); font-size:.95rem; border-top:1px solid rgba(255,255,255,.08); padding-top:10px;">
              <span>participants ${s.participants}</span>
              <span>min ${s.duration}</span>
            </div>
            <button class="btn">Start practice</button>
          </div>
        `).join("")}
      </section>
      `
    );
  },

  coach() {
    return Tpl.shell(
      "AI Coach",
      "Chat with your negotiation coach for live tips and support",
      `
      <section class="card chat reveal">
        <div id="chat-box" class="chat-box">
          <div class="bubble ai">Hi! I'm your negotiation coach. What's your goal for today's practice?</div>
        </div>
        <div class="chat-input">
          <input id="chat-input" type="text" placeholder="Type your question..." />
          <button id="chat-send" class="btn">Send</button>
        </div>
      </section>
      `
    );
  },

  analytics(data) {
    const k = `
      <section class="grid grid-2 reveal">
        <div class="card">
          <h3 style="margin-bottom:10px;">Recent scores</h3>
          <div class="grid" style="gap:10px;">
            ${data.recent.map(i => `
              <div class="card" style="display:flex; align-items:center; justify-content:space-between;">
                <span>${i.label}</span>
                <strong style="color:var(--primary)">${i.score}</strong>
              </div>`).join("")}
          </div>
        </div>
        <div class="card">
          <h3 style="margin-bottom:10px;">Suggestions</h3>
          <div class="grid" style="gap:10px;">
            ${data.tips.map(t => `
              <div class="card">
                <strong>${t.title}</strong>
                <p style="color:var(--muted); margin-top:6px;">${t.desc}</p>
              </div>`).join("")}
          </div>
        </div>
      </section>
    `;
    return Tpl.shell("Analytics", "Trends and insights to level-up your negotiation skills", k);
  },

  settings() {
    return Tpl.shell(
      "Settings",
      "Personalize your experience",
      `
        <section class="card grid grid-2 reveal">
          <div>
            <div style="font-weight:700">Interface language</div>
            <div style="color:var(--muted)">English (default)</div>
          </div>
          <div style="text-align:right">
            <button class="btn secondary">Change</button>
          </div>
        </section>
      `
    );
  },

  strategy() {
    return Tpl.shell(
      "Strategy Engine",
      "Answer the tailored questionnaire to get a personalized strategy report",
      `
      <section class="card stepper reveal">
        <div class="progress"><span id="step-progress"></span></div>
        <div id="stepper-root"><div style="text-align:center; color:var(--muted)">Loading questionnaire…</div></div>
        <div style="display:flex; gap:10px; justify-content:space-between; margin-top:16px;">
          <button id="btn-back" class="btn secondary" disabled>Back</button>
          <button id="btn-next" class="btn">Next</button>
        </div>
      </section>

      <section id="report-wrap" class="card reveal" style="margin-top:18px; display:none;">
        <h3 style="margin-bottom:10px;">Your generated report</h3>
        <iframe id="report-frame" class="report-frame" title="Negotiation report"></iframe>
      </section>
      `
    );
  }
};

// --------- App state ---------
const App = {
  root: document.getElementById("app-root"),
  navLinks: null,

  state: {
    questionnaire: null,
    answers: {},
    phaseIndex: 0
  },

  mock: {
    dashboard: {
      kpis: [
        { label: "Skill level", value: "Advanced" },
        { label: "Average score", value: "8.4" },
        { label: "Success rate", value: "78%" },
        { label: "Total negotiations", value: "47" }
      ],
      skills: [
        { name: "Communication", score: 85 },
        { name: "Strategy", score: 72 },
        { name: "Analysis", score: 90 },
        { name: "Creativity", score: 68 }
      ]
    },
    practice: [
      { title:"Business agreement", level:"Easy",   badgeCls:"easy",   skills:["Creativity","Active listening"], participants:2, duration:"15–10" },
      { title:"Real-estate deal",  level:"Hard",   badgeCls:"hard",   skills:["Strategy","Patience"],          participants:3, duration:"30–25" },
      { title:"Salary negotiation",level:"Medium", badgeCls:"medium", skills:["Confidence","Value framing"],   participants:2, duration:"20–15" },
    ],
    analytics: {
      recent: [
        { label:"Salary negotiation", score:"9.2" },
        { label:"Real-estate deal",   score:"7.8" },
        { label:"Business agreement", score:"8.9" }
      ],
      tips: [
        { title:"Evidence-based pitch", desc:"Use quantified outcomes and impact-oriented phrasing." },
        { title:"Sharpen your openers", desc:"Craft a strong opening line and rehearse delivery." }
      ]
    }
  },

  // --------- Router ---------
  handleRoute() {
    const page = (location.hash.slice(1) || "dashboard").toLowerCase();
    if (this.navLinks) {
      this.navLinks.forEach(a => a.classList.toggle("active", a.dataset.target === page));
    }
    this.render(page);
  },

  async render(page) {
    // Basic loading shimmer
    this.root.innerHTML = `<div class="card reveal" style="text-align:center; color:var(--muted)">Loading…</div>`;

    switch(page){
      case "dashboard":
        this.root.innerHTML = Tpl.dashboard(this.mock.dashboard);
        break;

      case "practice":
        this.root.innerHTML = Tpl.practice(this.mock.practice);
        break;

      case "analytics":
        this.root.innerHTML = Tpl.analytics(this.mock.analytics);
        break;

      case "coach":
        this.root.innerHTML = Tpl.coach();
        this.bindCoach();
        break;

      case "strategy":
        this.root.innerHTML = Tpl.strategy();
        await this.ensureSchema();
        this.renderStep();
        this.bindStepper();
        break;

      case "settings":
        this.root.innerHTML = Tpl.settings();
        break;

      default:
        this.root.innerHTML = `<div class="card">Page not found</div>`;
    }
  },

  init() {
    this.navLinks = document.querySelectorAll(".nav-link");
    window.addEventListener("hashchange", () => this.handleRoute());
    this.handleRoute();
  },

  // --------- AI Coach ---------
  bindCoach() {
    const box = document.getElementById("chat-box");
    const input = document.getElementById("chat-input");
    const send = document.getElementById("chat-send");

    const sendMsg = async () => {
      const msg = input.value.trim();
      if(!msg) return;
      box.insertAdjacentHTML("beforeend", `<div class="bubble me">${msg}</div>`);
      input.value = "";
      box.scrollTop = box.scrollHeight;

      const thinkingId = `t-${Date.now()}`;
      box.insertAdjacentHTML("beforeend", `<div id="${thinkingId}" class="bubble ai">...</div>`);

      try{
        const res = await fetch(`${API_BASE}/coach`, {
          method:"POST",
          headers:{ "Content-Type":"application/json" },
          body: JSON.stringify({ msg })
        });
        const data = await res.json();
        document.getElementById(thinkingId).textContent = data.reply || "OK";
      }catch{
        document.getElementById(thinkingId).textContent = "Error. Please try again.";
      }
      box.scrollTop = box.scrollHeight;
    };

    send.addEventListener("click", sendMsg);
    input.addEventListener("keydown", e => { if(e.key === "Enter") sendMsg(); });
  },

  // --------- Strategy stepper ---------
  async ensureSchema() {
    if (this.state.questionnaire) return;
    const res = await fetch(`${API_BASE}/questionnaire/schema`);
    if (!res.ok) throw new Error(`Failed to load schema: ${res.statusText}`);
    this.state.questionnaire = await res.json();
    this.state.phaseIndex = 0;
    this.state.answers = {};
  },

  bindStepper() {
    const back = document.getElementById("btn-back");
    const next = document.getElementById("btn-next");
    back.addEventListener("click", () => {
      this.collectAnswers();
      if (this.state.phaseIndex > 0) {
        this.state.phaseIndex--;
        this.renderStep();
      }
    });
    next.addEventListener("click", async () => {
      this.collectAnswers();
      const last = this.state.phaseIndex >= this.state.questionnaire.phases.length - 1;
      if (!last) {
        this.state.phaseIndex++;
        this.renderStep();
      } else {
        await this.finishStrategy();
      }
    });
  },

  renderStep() {
    const stepRoot = document.getElementById("stepper-root");
    const prog = document.getElementById("step-progress");
    const q = this.state.questionnaire;
    const idx = this.state.phaseIndex;
    const phase = q.phases[idx];

    const pct = Math.round(((idx) / q.phases.length) * 100);
    prog.style.width = `${pct}%`;

    const html = phase.questions.map(qq => this.renderQuestion(qq)).join("");
    stepRoot.innerHTML = html;

    // back button state
    document.getElementById("btn-back").disabled = (idx === 0);

    // click visuals for choices
    stepRoot.querySelectorAll(".choice input").forEach(inp => {
      inp.addEventListener("change", () => {
        if (inp.type === "radio") {
          stepRoot.querySelectorAll(`input[name="${inp.name}"]`).forEach(r => {
            r.closest(".choice").classList.toggle("selected", r.checked);
          });
        } else {
          inp.closest(".choice").classList.toggle("selected", inp.checked);
        }
      });
    });
  },

  renderQuestion(q) {
    const saved = this.state.answers[q.id];
    const label = `<div style="font-weight:700; margin-bottom:8px;">${q.question}</div>`;
    let inner = "";

    if (q.answerType === "single_choice") {
      inner = `
        <div class="grid" style="gap:10px;">
          ${(q.options || []).map(o => `
            <label class="choice ${saved === o.value ? "selected" : ""}">
              <input type="radio" name="${q.id}" value="${o.value}" ${saved === o.value ? "checked": ""} style="position:absolute; opacity:0; width:0; height:0;" />
              ${o.label}
            </label>`).join("")}
        </div>
      `;
    } else if (q.answerType === "multiple_choice") {
      const arr = Array.isArray(saved) ? saved : [];
      inner = `
        <div class="grid" style="gap:10px;">
          ${(q.options || []).map(o => `
            <label class="choice ${arr.includes(o.value) ? "selected" : ""}">
              <input type="checkbox" name="${q.id}" value="${o.value}" ${arr.includes(o.value) ? "checked": ""} style="position:absolute; opacity:0; width:0; height:0;" />
              ${o.label}
            </label>`).join("")}
        </div>
      `;
    } else if (q.answerType === "rating_scale") {
      inner = `<input class="input" type="number" min="${q.scaleMin}" max="${q.scaleMax}" name="${q.id}" value="${saved ?? ""}" placeholder="Enter ${q.scaleMin}–${q.scaleMax}" />`;
    } else if (q.answerType === "free_text_limited") {
      inner = `<textarea class="input" rows="3" name="${q.id}" placeholder="${(q.ui && q.ui.placeholder) || ""}">${saved ?? ""}</textarea>`;
    } else {
      inner = `<input class="input" type="text" name="${q.id}" value="${saved ?? ""}" placeholder="${(q.ui && q.ui.placeholder) || ""}" />`;
    }
    return `<div class="question">${label}${inner}</div>`;
  },

  collectAnswers() {
    const root = document.getElementById("stepper-root");
    if (!root) return;
    const formEls = root.querySelectorAll("input, textarea, select");
    const grouped = new Map();

    formEls.forEach(el => {
      if (!el.name) return;
      if (!grouped.has(el.name)) grouped.set(el.name, []);
      if (el.type === "checkbox") {
        if (el.checked) grouped.get(el.name).push(el.value);
      } else if (el.type === "radio") {
        if (el.checked) grouped.get(el.name).push(el.value);
      } else {
        if (el.value !== "") grouped.get(el.name).push(el.value);
      }
    });

    grouped.forEach((vals, key) => {
      this.state.answers[key] = vals.length > 1 ? vals : (vals[0] ?? "");
    });
  },

  async finishStrategy() {
    // show spinner state in the stepper area
    const stepRoot = document.getElementById("stepper-root");
    stepRoot.innerHTML = `<div style="text-align:center; color:var(--muted)">Generating report…</div>`;

    try{
      const res = await fetch(`${API_BASE}/questionnaire/report`, {
        method: "POST",
        headers: { "Content-Type":"application/json" },
        body: JSON.stringify({ answers: this.state.answers })
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.reason || "Failed to generate report");

      // fetch report HTML and embed
      const r = await fetch(data.report_url);
      if (!r.ok) throw new Error(`Cannot load report: ${r.statusText}`);
      const html = await r.text();

      const frame = document.getElementById("report-frame");
      const wrap = document.getElementById("report-wrap");
      wrap.style.display = "block";
      frame.srcdoc = html;

      // mark progress bar as full
      document.getElementById("step-progress").style.width = "100%";
    }catch(e){
      stepRoot.innerHTML = `<div class="card">Error: ${(e && e.message) || e}</div>`;
    }
  }
};

App.init();
