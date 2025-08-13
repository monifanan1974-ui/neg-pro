# NegotiationPro - AI-Powered Negotiation Training Platform

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
cp .env.example .env
# Edit .env with your API keys

# Using Docker (recommended)
docker-compose up -d

# Manual setup
pip install -r requirements.txt

# Run (Flask app object is `app` inside api.py)
gunicorn --bind 0.0.0.0:8000 --reload api:app

# Access application
# Health check:
# http://localhost:8000/health
