# backend/branching_sim.py
# Builds a small branching conversation tree with probabilities.

from typing import List, Dict

def build_branches(persona: str, culture: str, scenarios: List[Dict[str, str]]) -> List[Dict]:
    """
    Returns a list of branches:
    [
      {
        "path": ['Them: ...', 'You: ...', 'Them: ...'],
        "probability": 0.35
      }, ...
    ]
    """
    def find(trigger_contains: str) -> str:
        for s in scenarios:
            if trigger_contains.lower() in s["trigger"].lower():
                return s["reply"]
        return "Acknowledge, reframe to value, and bring back to core terms."

    # Three canonical branches
    b1 = {
        "path": [
            'Them: "Our budget is very tight."',
            f'You: "{find("Lowball")}"',
            'Them: "Can you justify the number?"',
            'You: "Two proof points: [impact #1], [impact #2]. Then this range is justified by source A/B."'
        ],
        "probability": 0.38 if "analyst" in (persona or "").lower() else 0.32
    }
    b2 = {
        "path": [
            'Them: "Let’s revisit next month."',
            f'You: "{find("Stall")}"',
            'Them: "Okay, what window do you need?"',
            'You: "Given my timeline, I propose a decision window of 5 business days."'
        ],
        "probability": 0.30 if culture == "high" else 0.28
    }
    b3 = {
        "path": [
            'Them: "We can add perks instead of base."',
            f'You: "{find("Change of Subject")}"',
            'Them: "Alright, what base makes sense then?"',
            'You: "Let’s align on scope and title, then I’ll map the base to the market median for that scope."'
        ],
        "probability": 0.40 if "friend" in (persona or "").lower() else 0.25
    }
    # Normalize probabilities to 1.0 (quick pass)
    total = b1["probability"] + b2["probability"] + b3["probability"]
    for b in (b1,b2,b3):
        b["probability"] = round(b["probability"]/total, 2)
    return [b1,b2,b3]

