# Texas P&C Study API

An API designed to **teach and automate studying** for the Texas General Lines Property & Casualty (P&C) Insurance License Exam (Pearson VUE).

## Features
- Structured learning modules based on official exam content outlines
- Interactive quizzes with explanations
- Progress tracking per user/session
- Spaced repetition helpers
- Texas-specific high-yield facts (30/60/25, TWIA vs FAIR Plan, nonsubscriber WC, etc.)
- Ready for local development or deployment (FastAPI + Uvicorn)

## Quick Start

```bash
git clone https://github.com/thriftexport/texas-pc-study-api.git
cd texas-pc-study-api
python -m venv venv
source venv/bin/activate  # or venv\\Scripts\\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/docs for interactive Swagger UI.

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/modules` | List all study modules |
| GET | `/modules/{module_id}` | Get full module content |
| GET | `/quiz/{module_id}` | Generate quiz for a module |
| POST | `/quiz/submit` | Submit answers and get score + explanations |
| GET | `/progress/{user_id}` | Get study progress |
| POST | `/progress` | Update progress |
| GET | `/texas-cheatsheet` | High-yield Texas facts |
| GET | `/study-session` | Start an automated study session |

## Exam Context
- 145 questions (130 scored + 15 pretest)
- 150 minutes
- 70% to pass
- No pre-licensing education required for permanent license
- Heavy focus on Texas rules (~30 questions)

Built for efficient, automated exam preparation.
