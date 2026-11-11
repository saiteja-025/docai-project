from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
from backend.db.session import get_db
from backend.db.models import User, Document, Quiz, QuizResult
from backend.api.deps import get_current_user
from backend.services.generation_service import generate_mcqs

router = APIRouter()


class QuizResponse(BaseModel):
    questions: list


class QuizSubmitRequest(BaseModel):
    quiz_id: int = 0
    score: float
    answers_json: str = "{}"


@router.get("/{doc_id}")
def get_quiz(
    doc_id: int,
    difficulty: str = "medium",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    if doc.status != "ready":
        raise HTTPException(status_code=400, detail="Document is not ready for quiz generation.")

    # Use content_text first (most complete), fall back to summary_detailed, then title
    text_to_quiz = None
    if doc.content_text and len(doc.content_text.strip()) > 100:
        text_to_quiz = doc.content_text
    elif doc.summary_detailed and len(doc.summary_detailed.strip()) > 50:
        text_to_quiz = doc.summary_detailed
    else:
        text_to_quiz = doc.title

    try:
        mcqs_json_str = generate_mcqs(text_to_quiz, difficulty)

        # Try to parse — handle both array and object responses
        try:
            mcqs_list = json.loads(mcqs_json_str)
        except json.JSONDecodeError:
            # Strip any remaining markdown and retry
            cleaned = mcqs_json_str.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            mcqs_list = json.loads(cleaned)

        if not isinstance(mcqs_list, list) or len(mcqs_list) == 0:
            raise ValueError("Groq returned empty or invalid question array.")

        # Validate each question has required fields
        validated = []
        for q in mcqs_list:
            if isinstance(q, dict) and "question" in q and "options" in q and "correct_answer" in q:
                if "explanation" not in q:
                    q["explanation"] = "No explanation provided."
                validated.append(q)

        if not validated:
            raise ValueError("No valid questions found in Groq response.")

        return {"questions": validated}

    except Exception as e:
        print(f"[Quiz] Error generating quiz for doc {doc_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz: {str(e)}"
        )


@router.post("/submit")
def submit_quiz(
    request: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # quiz_id=0 means client sent no specific quiz record — store as NULL
    valid_quiz_id = request.quiz_id if request.quiz_id and request.quiz_id > 0 else None

    result = QuizResult(
        user_id=current_user.id,
        quiz_id=valid_quiz_id,
        score=request.score,
        answers_json=request.answers_json
    )
    db.add(result)
    db.commit()
    return {"message": "Quiz submitted successfully.", "score": request.score}
