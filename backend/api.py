import os
from flask import Flask, send_from_directory, jsonify, request, redirect, url_for
from flask_cors import CORS

# יצירת האפליקציה
app = Flask(__name__)
CORS(app)

# קביעת נתיבים לסטטיים
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


@app.route("/")
def root():
    """Redirect root to the app."""
    return redirect("/app/")


@app.route("/app/")
def app_index():
    """Serve the main frontend index.html"""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/app/<path:fn>")
def app_files(fn):
    """Serve files from frontend/"""
    return send_from_directory(FRONTEND_DIR, fn)


@app.route("/frontend/<path:fn>")
def frontend_files(fn):
    """Serve files from frontend/ (explicit path)"""
    return send_from_directory(FRONTEND_DIR, fn)


@app.route("/public/<path:fn>")
def public_files(fn):
    """Serve files from public/"""
    return send_from_directory(PUBLIC_DIR, fn)


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "ok",
            "service": "NegotiationPro API",
            "version": "2025-08-12",
            "frontend_dir": FRONTEND_DIR,
            "frontend_exists": os.path.exists(FRONTEND_DIR),
            "frontend_files": os.listdir(FRONTEND_DIR)
            if os.path.exists(FRONTEND_DIR)
            else [],
            "public_dir": PUBLIC_DIR,
            "public_exists": os.path.exists(PUBLIC_DIR),
            "public_files": os.listdir(PUBLIC_DIR)
            if os.path.exists(PUBLIC_DIR)
            else [],
            "active_static_root": FRONTEND_DIR,
        }
    )


@app.route("/questionnaire/report", methods=["GET", "POST"])
def questionnaire_report():
    """Main endpoint to handle questionnaire report requests"""
    # כאן תישאר הלוגיקה הקיימת שלך ליצירת דוח
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    # דוגמה למענה זמני
    return jsonify({"status": "ok", "echo": data})


# Alias endpoint: /report -> /questionnaire/report
@app.route("/report", methods=["GET", "POST"])
def report_alias():
    return redirect(url_for("questionnaire_report"), code=307)


if __name__ == "__main__":
    print("==== NegotiationPro API ====")
    print(f"Listening on http://localhost:5000 (Debug=True)")
    print(f"[static root] frontend = {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=5000, debug=True)
