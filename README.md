--- START OF FILE README.md ---
<img width="1278" height="535" alt="image" src="https://github.com/user-attachments/assets/42357e87-828a-4c8a-a8f5-0a81531ec941" /># NegotiationPro - AI-Powered Negotiation Training Platform

## 🎯 Overview
Advanced AI-powered negotiation simulation engine for practicing complex scenarios, receiving real-time feedback, and improving negotiation skills through personalized training.

## 🚀 Features
- **Advanced AI Engine**: Complex conversation simulation with logical branching
- **Persona Profiling**: Adaptive responses to different personality types
- **Real-time Strategy**: Battle card integration with market intelligence
- **Performance Analytics**: Comprehensive feedback and progress tracking
- **Multi-language Support**: Hebrew, English, and additional languages
- **Team Collaboration**: Group negotiation scenarios

## 🛠️ Tech Stack
- **Backend**: Python (Flask)
- **Frontend**: HTML, CSS, JavaScript (Progressive Web App)
- **Database**: Firebase with Redis caching
- **AI/ML**: OpenAI GPT, custom NLP models
- **Deployment**: Docker, CI/CD pipeline

## 📦 Quick Start
```bash
# Clone repository
git clone https://github.com/monifanan1974-ui/neg-pro.git
cd neg-pro

# Setup environment
# Create a .env file from the example (see .env.example)
cp .env.example .env

# Edit the .env file with your API keys (e.g., OPENAI_API_KEY)
# For Google Translate, ensure you are authenticated via gcloud CLI:
# gcloud auth application-default login

# Install dependencies
pip install -r requirements.txt

# Run the application (Flask development server)
python api.py

# Access application in your browser
http://localhost:5000
