# backend/battlecard_integration_plus.py
"""Battlecard endpoint (clean, English-only).

POST /chat
Accepts one of:
  1) {"inputs": {...}}                  -> direct call to engine
  2) {"questionnaire": {...}, "schema_map": {...}} -> map answers to inputs then call engine
  3) {"demo": true}                     -> use example inputs from bundled template

Env override for the template path: BATTLECARD_TEMPLATE.
"""

import os
import json
from flask import request, jsonify
from .battle_card_engine import BattleCardEngine
from .questionnaire_mapper import map_questionnaire_to_inputs

def _resolve_default_template() -> str:
    env_path = os.environ.get("BATTLECARD_TEMPLATE")
    if env_path:
        return env_path
    candidates = [
        os.path.join("data", "battle_card_locked.template.json"),
        "./battle_card_locked.template.json",
        os.path.join("..", "data", "battle_card_locked.template.json"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Fallback
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "data", "battle_card_locked.template.json")

def register_battlecard_routes(app, route: str = "/chat"):
    engine = BattleCardEngine()

    @app.route(route, methods=["POST"])
    def chat():
      try:
          payload = request.get_json(force=True, silent=False) or {}
      except Exception:
          return jsonify({"error": "invalid JSON"}), 400

      # DEMO
      if payload.get("demo") is True:
          try:
              path = _resolve_default_template()
              with open(path, "r", encoding="utf-8") as f:
                  tpl = json.load(f)
              example_inputs = tpl.get("example_generation", {}).get("inputs_example", {})
              card = engine.generate(inputs=example_inputs)
              return jsonify(card), 200
          except Exception as e:
              return jsonify({"error": f"demo failed: {e}"}), 500

      # Direct inputs
      inputs = None
      if "inputs" in payload:
          inputs = payload["inputs"]

      # Or mapped from questionnaire
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
