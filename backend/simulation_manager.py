# backend/simulation_manager.py
# (Unchanged helper, kept for completeness and future simulations.)

class SimulationManager:
    def __init__(self, playlets, dilemmas):
        self.playlets = playlets.get("playlets", [])
        self.dilemmas = dilemmas.get("dilemmas", [])
    
    def get_relevant_scenario(self, user_profile):
        for playlet in self.playlets:
            if user_profile.get("persona") in playlet.get("persona_fit", []):
                return playlet
        user_issues = user_profile.get("issues", [])
        for dilemma in self.dilemmas:
            common_triggers = dilemma.get("common_triggers", [])
            for issue in user_issues:
                if issue in common_triggers:
                    return {"type": "dilemma", "content": dilemma}
        return None

