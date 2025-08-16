/* frontend/report_embed.js — helpers for embedding/printing reports */

/**
 * Inject given HTML content into a target iframe (by id).
 * Creates iframe if missing and appends into container if provided.
 */
function embedReportHTML({ html, iframeId = "report-frame", containerId = null }) {
  let iframe = document.getElementById(iframeId);
  if (!iframe) {
    iframe = document.createElement("iframe");
    iframe.id = iframeId;
    iframe.className = "report-frame";
    if (containerId) {
      const parent = document.getElementById(containerId);
      (parent || document.body).appendChild(iframe);
    } else {
      document.body.appendChild(iframe);
    }
  }
  iframe.srcdoc = html;
  return iframe;
}

/** Open printable report in a new window (optional) */
function openReportWindow(html) {
  const win = window.open("", "_blank", "noopener,noreferrer,width=1200,height=900");
  if (!win) return;
  win.document.open();
  win.document.write(html);
  win.document.close();
}
