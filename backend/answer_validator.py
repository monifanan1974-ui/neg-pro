# backend/answer_validator.py  (only the __init__ changed to accept external validation_schema.json)
import logging
logger = logging.getLogger("AnswerValidator")

class AnswerValidator:
    def __init__(self, schema, external_schema: dict = None):
        """
        schema: derived from questionnaire.json (fallback)
        external_schema: if data/validation_schema.json exists, it overrides types/required/options
        """
        if external_schema and external_schema.get("questions"):
            self.schema = external_schema
        else:
            self.schema = schema or {"questions":[]}
        self.question_map = {q["id"]: q for q in self.schema.get("questions", [])}

    def validate(self, answers: dict):
        errors = []
        if not isinstance(answers, dict):
            return ["Invalid answers payload"]

        for qid, meta in self.question_map.items():
            val = answers.get(qid)
            # Required
            if meta.get("required"):
                if val is None or (isinstance(val, str) and val.strip() == "") or (isinstance(val, list) and len(val) == 0):
                    errors.append(f"{qid} is required.")
                    continue
            # Type checks
            expected = meta.get("type", "string")
            if expected == "list" and val is not None and not isinstance(val, list):
                errors.append(f"{qid} must be a list.")
            if expected == "number" and val is not None:
                try:
                    float(str(val).replace(",","").replace("€","").replace("$",""))
                except Exception:
                    errors.append(f"{qid} must be numeric.")
            # Options
            opts = meta.get("options")
            if opts and isinstance(val, str) and val not in opts:
                errors.append(f"Invalid option for {qid}.")
        return errors

