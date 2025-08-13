import os
from flask import Flask, send_from_directory, jsonify, request, redirect, url_for, Response
from flask_cors import CORS

# === Setup ===
app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# === Routes ===

@app.route("/")
def root():
    """Redirect root to /app/"""
    return redirect("/app/")

@app.route("/app/")
def app_index():
    """Serve frontend index.html"""
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/app/<path:fn>")
def app_files(fn):
    """Serve other frontend files"""
    return send_from_directory(FRONTEND_DIR, fn)

@app.route("/frontend/<path:fn>")
def frontend_files(fn):
    """Serve frontend assets"""
    return send_from_directory(FRONTEND_DIR, fn)

@app.route("/public/<path:fn>")
def public_files(fn):
    """Serve public/ files"""
    return send_from_directory(PUBLIC_DIR, fn)

@app.route("/health")
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "NegotiationPro API",
        "version": "2025-08-12",
        "frontend_dir": FRONTEND_DIR,
        "frontend_exists": os.path.exists(FRONTEND_DIR),
        "frontend_files": os.listdir(FRONTEND_DIR) if os.path.exists(FRONTEND_DIR) else [],
        "public_dir": PUBLIC_DIR,
        "public_exists": os.path.exists(PUBLIC_DIR),
        "public_files": os.listdir(PUBLIC_DIR) if os.path.exists(PUBLIC_DIR) else [],
        "active_static_root": FRONTEND_DIR
    })

@app.route("/questionnaire/report", methods=["GET", "POST"])
def questionnaire_report():
    """Main report endpoint"""
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    # כאן תוסיף את הלוגיקה האמיתית שלך להפקת הדוח
    # כרגע דוגמה בלבד
    html_report = f"""
    <html>
    <head><title>Negotiation Report</title></head>
    <body>
        <h1>NegotiationPro Report</h1>
        <pre>{data}</pre>
    </body>
    </html>
    """
    return Response(html_report, mimetype="text/html")

# === NEW: Alias /report to /questionnaire/report (returns HTML directly) ===
@app.route("/report", methods=["GET", "POST"])
def report_alias():
    """Direct HTML report"""
    try:
        if request.method == "POST":
            data = request.get_json(force=True)
        else:
            data = {"status": "no POST data received"}
    except Exception:
        data = {"status": "error", "message": "Invalid JSON"}

    html_report = f"""
    <html>
    <head><title>Negotiation Report</title></head>
    <body>
        <h1>NegotiationPro Report</h1>
        <pre>{data}</pre>
    </body>
    </html>
    """
    return Response(html_report, mimetype="text/html")

# === Run ===
if __name__ == "__main__":
    print("==== NegotiationPro API ====")
    print("Listening on http://localhost:5000 (Debug=True)")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=5000, debug=True)
