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
    
    text_to_quiz = doc.summary_detailed if doc.summary_detailed else doc.title
    
    # Generate MCQs based on summary detailed text.
    try:
        mcqs_json_str = generate_mcqs(text_to_quiz, difficulty)
        mcqs_list = json.loads(mcqs_json_str)
        if not isinstance(mcqs_list, list) or len(mcqs_list) == 0:
            raise ValueError("Groq returned empty or invalid question array.")
        return {"questions": mcqs_list}
    except Exception as e:
        print(f"Error serving quiz: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz with Groq AI: {str(e)}"
        )

@router.post("/submit")
def submit_quiz(
    request: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # If quiz_id is 0 or invalid FK, set to None so PostgreSQL does not violate foreign key constraint
    valid_quiz_id = request.quiz_id if request.quiz_id and request.quiz_id > 0 else None
    result = QuizResult(
        user_id=current_user.id,
        quiz_id=valid_quiz_id,
        score=request.score,
        answers_json=request.answers_json
    )
    db.add(result)
    db.commit()
    return {"message": "Quiz submitted successfully."}
