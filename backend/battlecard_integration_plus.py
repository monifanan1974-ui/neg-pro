# backend/battlecard_integration_plus.py
import os, json
from flask import request, jsonify
from battle_card_engine import BattleCardEngine
from questionnaire_mapper import map_questionnaire_to_inputs

def _resolve_default_template():
    env_path = os.environ.get("BATTLECARD_TEMPLATE")
    if env_path:
        return env_path
    candidates = [
        "data/battle_card_locked.template.json",
        "./battle_card_locked.template.json",
        "../data/battle_card_locked.template.json",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return "data/battle_card_locked.template.json"

def register_battlecard_routes(app, route="/chat"):
    template_path = _resolve_default_template()
    data_root = os.environ.get("BATTLECARD_DATA_ROOT", os.path.dirname(template_path) or ".")
    engine = BattleCardEngine(template_path=template_path, data_root=data_root)

    @app.route(route, methods=["POST"])
    def battlecard_chat():
        """
        מקבל:
          1) {"inputs": {...}}  - שליחה ישירה למנוע
          2) {"questionnaire": {...}, "schema_map": {...}} - ממפה ואז מריץ
          3) {"demo": true} - דמו מהתבנית
        """
        payload = request.get_json(force=True, silent=True) or {}

        if payload.get("demo"):
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    tpl = json.load(f)
                inputs = tpl.get("example_generation", {}).get("inputs_example", {})
                return jsonify(engine.generate(inputs=inputs)), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        if "inputs" in payload:
            inputs = payload["inputs"]
        elif "questionnaire" in payload:
            answers = payload.get("questionnaire") or {}
            schema_map = payload.get("schema_map") or {}
            try:
                inputs = map_questionnaire_to_inputs(answers, schema_map)
            except Exception as e:
                return jsonify({"error": f"questionnaire mapping failed: {e}"}), 400
        else:
            return jsonify({"error": "missing 'inputs' or 'questionnaire' or 'demo'"}), 400

        try:
            card = engine.generate(inputs=inputs)
            return jsonify(card), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

