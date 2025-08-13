const API_BASE = window.location.origin;

async function buildReport(payload) {
    const res = await fetch(`${API_BASE}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (!res.ok) {
        document.getElementById("report").innerHTML = `<p style="color:red">Error: ${res.status}</p>`;
        return;
    }

    const contentType = res.headers.get("Content-Type") || "";
    if (contentType.includes("text/html")) {
        document.getElementById("report").innerHTML = await res.text();
    } else {
        const json = await res.json();
        document.getElementById("report").innerHTML = `<pre>${JSON.stringify(json, null, 2)}</pre>`;
    }
}
