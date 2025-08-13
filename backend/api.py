import os
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# === Serve frontend directly from root ===
@app.route("/")
def serve_root():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:fn>")
def serve_frontend_files(fn):
    if os.path.exists(os.path.join(FRONTEND_DIR, fn)):
        return send_from_directory(FRONTEND_DIR, fn)
    return jsonify({"error": "File not found"}), 404

@app.route("/public/<path:fn>")
def serve_public_files(fn):
    return send_from_directory(PUBLIC_DIR, fn)

@app.route("/health")
def health():
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
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    return jsonify({"status": "ok", "echo": data})

# Alias /report to /questionnaire/report
@app.route("/report", methods=["GET", "POST"])
def report_alias():
    return questionnaire_report()

if __name__ == "__main__":
    print("==== NegotiationPro API ====")
    print("Listening on http://localhost:5000 (Debug=True)")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=5000, debug=True)
