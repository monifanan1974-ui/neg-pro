# backend/api.py

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    """
    Simple health check endpoint used by CI.
    Must be exactly '/health' (lowercase) and return HTTP 200.
    """
    return jsonify(status="ok"), 200


@app.route("/questionnaire/report", methods=["POST"])
def questionnaire_report():
    """
    Receives questionnaire data, validates it, and prepares it for report generation.
    """
    # 1) Safely parse JSON
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify(error="Invalid JSON"), 400

    # 2) Minimal validation example
    if "questionnaire" not in payload:
        return jsonify(error="Missing 'questionnaire' key"), 400

    # 3) Placeholder processing
    return jsonify(status="success", message="Questionnaire received"), 200


if __name__ == "__main__":
    # Bind to all interfaces so it also runs in containers/VMs
    app.run(host="0.0.0.0", port=8000, debug=False)
