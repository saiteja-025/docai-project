from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import User, Document
from backend.api.deps import get_current_user
from backend.services.cloudinary_service import upload_pdf_to_cloudinary
from backend.services.rag_service import process_and_store_document
from backend.services.generation_service import generate_summary

router = APIRouter()

def process_document_background(file_bytes: bytes, doc_id: int, filename: str):
    from backend.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Process and store in FAISS
        text = process_and_store_document(file_bytes, str(doc_id), filename)
        
        # Generate summary
        summary = generate_summary(text)
        
        # Update db
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            import json
            doc.status = "ready"
            
            short_summary = summary.get("short", "")
            doc.summary_short = json.dumps(short_summary) if isinstance(short_summary, (dict, list)) else str(short_summary)
            
            detailed_summary = summary.get("detailed", "")
            doc.summary_detailed = json.dumps(detailed_summary) if isinstance(detailed_summary, (dict, list)) else str(detailed_summary)
            
            db.commit()
    except Exception as e:
        print(f"Error processing document: {e}")
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "failed"
            db.commit()
    finally:
        db.close()

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are supported.")
    
    file_bytes = await file.read()
    
    # 1. Upload to Cloudinary
    cloudinary_url = upload_pdf_to_cloudinary(file_bytes, file.filename)
    
    # 2. Create DB Record
    doc = Document(
        title=file.filename,
        cloudinary_url=cloudinary_url,
        owner_id=current_user.id,
        status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # 3. Add background task for RAG parsing and Summarization
    background_tasks.add_task(process_document_background, file_bytes, doc.id, file.filename)
    
    return {"id": doc.id, "title": doc.title, "status": doc.status, "message": "Document is processing."}

@router.get("/")
def get_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return [{"id": d.id, "title": d.title, "status": d.status, "created_at": d.created_at} for d in docs]

@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Explicitly clear dependent records to ensure SQLite does not leave orphaned files or throw if constraints applied
    from backend.db.models import ChatSession, Quiz, ChatMessage, QuizResult
    chat_sessions = db.query(ChatSession).filter(ChatSession.document_id == doc_id).all()
    for cs in chat_sessions:
        db.query(ChatMessage).filter(ChatMessage.session_id == cs.id).delete(synchronize_session=False)
    db.query(ChatSession).filter(ChatSession.document_id == doc_id).delete(synchronize_session=False)

    quizzes = db.query(Quiz).filter(Quiz.document_id == doc_id).all()
    for q in quizzes:
        db.query(QuizResult).filter(QuizResult.quiz_id == q.id).delete(synchronize_session=False)
    db.query(Quiz).filter(Quiz.document_id == doc_id).delete(synchronize_session=False)

    db.delete(doc)
    db.commit()
    return {"message": "Document deleted successfully."}
