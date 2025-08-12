# Import necessary libraries from Flask
# request: to handle incoming data from the request
# jsonify: to create a proper JSON response with headers
from flask import Flask, request, jsonify

# Initialize the Flask application
app = Flask(__name__)

# Define the endpoint for processing the questionnaire report
# It only accepts POST requests
@app.post("/questionnaire/report")
def questionnaire_report():
    """
    Receives questionnaire data, validates it, and prepares it for report generation.
    """
    # --- Step 1: Securely get the JSON payload ---
    # request.get_json(silent=True) will return None if the request is not a valid JSON,
    # instead of crashing the application.
    payload = request.get_json(silent=True)

    # --- Step 2: Input Validation ---
    # This is the "bouncer" at the door of your API.

    # Check 1: Was there any JSON payload at all?
    if payload is None:
        # Return a 400 Bad Request error with a clear message
        return jsonify({"error": "Invalid request: The request body must be a valid JSON."}), 400

    # Check 2: Try to get the answers dictionary from the payload.
    # We flexibly check for 'questionnaire' or 'answers' as the key.
    answers = payload.get("questionnaire") or payload.get("answers")

    # Check 3: Is the 'answers' block a dictionary?
    # isinstance() is the correct way to check the type of a variable.
    if not isinstance(answers, dict):
        return jsonify({"error": "Invalid data format: The 'answers' or 'questionnaire' field must be a dictionary."}), 400

    # Check 4: Is the dictionary of answers empty?
    if not answers:
        return jsonify({"error": "Invalid data: The 'answers' dictionary cannot be empty."}), 400

    # --- Step 3: If all checks passed, proceed with the logic ---
    
    # At this point, we know that 'answers' is a non-empty dictionary.
    # We can now safely work with it.
    
    # For debugging and development, it's good to print what you received.
    print("Received valid answers for processing:", answers)

    # TODO: Add your actual logic here.
    # For example, call the negotiation engine, generate the report, etc.
    # engine_result = advanced_negotiation_engine.process(answers)

    # --- Step 4: Return a success response ---
    # Return a 200 OK status with a confirmation message.
    # It's good practice to return the data you received to confirm it was processed correctly.
    return jsonify({
        "status": "success",
        "message": "Questionnaire data received and validated successfully.",
        "received_data": answers
    }), 200

# This part allows you to run the Flask server directly for testing
if __name__ == "__main__":
    # debug=True allows the server to auto-reload when you save changes
    app.run(debug=True, port=5000)
