from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import random
import uuid
from datetime import datetime

from app.data import MODULES, TEXAS_CHEATSHEET, QUIZ_BANK

app = FastAPI(
    title="Texas P&C Study API",
    description="Teach and automate studying for the Texas Property & Casualty Insurance License Exam",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory progress store (replace with DB in production)
PROGRESS_DB: Dict[str, Dict] = {}


class QuizAnswer(BaseModel):
    question_id: str
    selected_option: str


class QuizSubmission(BaseModel):
    user_id: Optional[str] = None
    module_id: str
    answers: List[QuizAnswer]


class ProgressUpdate(BaseModel):
    user_id: str
    module_id: str
    score: Optional[float] = None
    completed: bool = False
    notes: Optional[str] = None


@app.get("/")
def root():
    return {
        "name": "Texas P&C Study API",
        "version": "1.0.0",
        "description": "API to teach and automate studying for the Texas General Lines Property & Casualty Insurance License Exam",
        "docs": "/docs",
        "exam_info": {
            "questions": "145 total (130 scored + 15 pretest)",
            "time_limit": "150 minutes",
            "passing_score": "70% scaled",
            "prelicensing": "Not required for permanent license",
        },
    }


@app.get("/modules")
def list_modules():
    """List all available study modules."""
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "description": m["description"],
            "priority": m.get("priority", "medium"),
            "estimated_minutes": m.get("estimated_minutes", 30),
        }
        for m in MODULES
    ]


@app.get("/modules/{module_id}")
def get_module(module_id: str):
    """Get full content of a study module."""
    for m in MODULES:
        if m["id"] == module_id:
            return m
    raise HTTPException(status_code=404, detail="Module not found")


@app.get("/texas-cheatsheet")
def get_cheatsheet():
    """High-yield Texas-specific facts that appear frequently on the exam."""
    return TEXAS_CHEATSHEET


@app.get("/quiz/{module_id}")
def generate_quiz(
    module_id: str,
    num_questions: int = Query(default=5, ge=1, le=20),
):
    """Generate a randomized quiz for a module."""
    questions = QUIZ_BANK.get(module_id, [])
    if not questions:
        # Fallback: try general or return empty
        questions = QUIZ_BANK.get("general", [])
    if not questions:
        raise HTTPException(status_code=404, detail="No quiz available for this module")

    selected = random.sample(questions, min(num_questions, len(questions)))
    # Hide correct answers from response
    quiz = []
    for q in selected:
        quiz.append(
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"],
                "module": module_id,
            }
        )
    return {
        "module_id": module_id,
        "num_questions": len(quiz),
        "questions": quiz,
        "instructions": "Submit answers to /quiz/submit",
    }


@app.post("/quiz/submit")
def submit_quiz(submission: QuizSubmission):
    """Grade a quiz submission and return detailed feedback."""
    questions = {q["id"]: q for q in QUIZ_BANK.get(submission.module_id, [])}
    if not questions:
        questions = {q["id"]: q for q in QUIZ_BANK.get("general", [])}

    results = []
    correct_count = 0

    for ans in submission.answers:
        q = questions.get(ans.question_id)
        if not q:
            results.append(
                {
                    "question_id": ans.question_id,
                    "correct": False,
                    "message": "Question not found",
                }
            )
            continue

        is_correct = ans.selected_option.strip().upper() == q["correct"].strip().upper()
        if is_correct:
            correct_count += 1

        results.append(
            {
                "question_id": ans.question_id,
                "question": q["question"],
                "selected": ans.selected_option,
                "correct_answer": q["correct"],
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            }
        )

    total = len(submission.answers) or 1
    score = round((correct_count / total) * 100, 1)

    # Auto-update progress if user_id provided
    if submission.user_id:
        if submission.user_id not in PROGRESS_DB:
            PROGRESS_DB[submission.user_id] = {"modules": {}, "created": datetime.utcnow().isoformat()}
        PROGRESS_DB[submission.user_id]["modules"][submission.module_id] = {
            "last_score": score,
            "last_attempt": datetime.utcnow().isoformat(),
            "attempts": PROGRESS_DB[submission.user_id]["modules"].get(submission.module_id, {}).get("attempts", 0) + 1,
        }

    return {
        "score_percent": score,
        "correct": correct_count,
        "total": total,
        "passed": score >= 70,
        "results": results,
        "recommendation": "Review explanations for missed questions. Aim for consistent 80%+ before exam day."
        if score < 80
        else "Strong performance! Keep reinforcing with spaced review.",
    }


@app.get("/progress/{user_id}")
def get_progress(user_id: str):
    """Retrieve study progress for a user."""
    if user_id not in PROGRESS_DB:
        return {"user_id": user_id, "modules": {}, "message": "No progress recorded yet"}
    return {"user_id": user_id, **PROGRESS_DB[user_id]}


@app.post("/progress")
def update_progress(update: ProgressUpdate):
    """Manually update or create progress record."""
    if update.user_id not in PROGRESS_DB:
        PROGRESS_DB[update.user_id] = {"modules": {}, "created": datetime.utcnow().isoformat()}

    current = PROGRESS_DB[update.user_id]["modules"].get(update.module_id, {})
    current.update(
        {
            "completed": update.completed,
            "last_score": update.score if update.score is not None else current.get("last_score"),
            "notes": update.notes,
            "updated": datetime.utcnow().isoformat(),
        }
    )
    PROGRESS_DB[update.user_id]["modules"][update.module_id] = current
    return {"status": "updated", "user_id": update.user_id, "module_id": update.module_id}


@app.get("/study-session")
def start_study_session(
    user_id: Optional[str] = None,
    focus: Optional[str] = Query(None, description="module_id to focus on"),
):
    """Generate an automated study session recommendation."""
    session_id = str(uuid.uuid4())[:8]

    # Simple recommendation logic
    recommended_modules = [m["id"] for m in MODULES if m.get("priority") == "high"]
    if focus and any(m["id"] == focus for m in MODULES):
        recommended_modules = [focus] + [m for m in recommended_modules if m != focus]

    session = {
        "session_id": session_id,
        "user_id": user_id or "anonymous",
        "created": datetime.utcnow().isoformat(),
        "recommended_path": [
            {"step": 1, "action": "Review Texas Cheat Sheet", "endpoint": "/texas-cheatsheet"},
            {"step": 2, "action": f"Study module: {recommended_modules[0] if recommended_modules else 'foundations'}", "endpoint": f"/modules/{recommended_modules[0] if recommended_modules else 'foundations'}"},
            {"step": 3, "action": "Take a 5-question quiz", "endpoint": f"/quiz/{recommended_modules[0] if recommended_modules else 'foundations'}?num_questions=5"},
            {"step": 4, "action": "Submit answers and review explanations", "endpoint": "/quiz/submit"},
            {"step": 5, "action": "Update progress", "endpoint": "/progress"},
        ],
        "tips": [
            "Focus first on Texas-specific rules (TWIA, FAIR Plan, 30/60/25, nonsubscriber WC).",
            "Aim for 80%+ on practice quizzes before moving on.",
            "Use spaced repetition: revisit weak modules after 1 day, 3 days, 7 days.",
        ],
    }
    return session


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
