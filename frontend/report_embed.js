// frontend/report_embed.js
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
