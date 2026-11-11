from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import User, Document
from backend.api.deps import get_current_user
from backend.services.cloudinary_service import upload_pdf_to_cloudinary, delete_from_cloudinary
from backend.services.rag_service import process_and_store_document, extract_text
from backend.services.generation_service import generate_summary

router = APIRouter()

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB limit


def process_document_background(file_bytes: bytes, doc_id: int, filename: str, db_session_factory=None):
    """
    Background document processing — split into independent stages so a failure
    in one stage (e.g. Groq timeout) never leaves the document stuck on 'processing'.

    Stage 1  — Text extraction           → marks doc 'ready' immediately
    Stage 2  — FAISS vector indexing     → non-fatal if it fails
    Stage 3  — Groq AI summary           → non-fatal if it fails
    """
    import json
    if db_session_factory:
        db = db_session_factory()
    else:
        from backend.db.session import SessionLocal
        db = SessionLocal()

    doc = None
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            print(f"[BG] Document {doc_id} not found in DB — aborting.")
            return

        # ----------------------------------------------------------------
        # STAGE 1: Text extraction — fast, never fails hard
        # ----------------------------------------------------------------
        print(f"[BG] Stage 1 — Extracting text from '{filename}'...")
        try:
            text = extract_text(file_bytes, filename)
            if not text or not text.strip():
                text = f"No readable text could be extracted from '{filename}'."
        except Exception as e:
            print(f"[BG] Stage 1 — Text extraction error (using placeholder): {e}")
            text = f"Text extraction failed for '{filename}': {e}"

        # Persist text and mark READY immediately so the user is unblocked
        doc.content_text = text
        doc.status = "ready"
        db.commit()
        print(f"[BG] Stage 1 — Document {doc_id} marked READY. Text length: {len(text)} chars.")

        # ----------------------------------------------------------------
        # STAGE 2: FAISS vector indexing — non-fatal
        # ----------------------------------------------------------------
        print(f"[BG] Stage 2 — Building FAISS vector index for doc {doc_id}...")
        try:
            from backend.services.rag_service import process_and_store_document
            process_and_store_document(file_bytes, str(doc_id), filename)
            print(f"[BG] Stage 2 — FAISS index built successfully for doc {doc_id}.")
        except Exception as e:
            print(f"[BG] Stage 2 — FAISS indexing failed (non-fatal, chat may use full text): {e}")

        # ----------------------------------------------------------------
        # STAGE 3: Groq AI Summary — non-fatal
        # ----------------------------------------------------------------
        print(f"[BG] Stage 3 — Generating AI summary for doc {doc_id}...")
        try:
            summary = generate_summary(text)

            # Re-fetch doc in case it was refreshed
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if doc:
                short_summary = summary.get("short", "")
                detailed_summary = summary.get("detailed", "")
                doc.summary_short = (
                    json.dumps(short_summary)
                    if isinstance(short_summary, (dict, list))
                    else str(short_summary)
                )
                doc.summary_detailed = (
                    json.dumps(detailed_summary)
                    if isinstance(detailed_summary, (dict, list))
                    else str(detailed_summary)
                )
                db.commit()
                print(f"[BG] Stage 3 — AI summary saved for doc {doc_id}.")
        except Exception as e:
            print(f"[BG] Stage 3 — Summary generation failed (non-fatal, doc remains ready): {e}")

    except Exception as e:
        # Only reaches here if DB itself fails — still try to mark failed
        print(f"[BG] Critical error processing document {doc_id}: {e}")
        try:
            if doc:
                doc.status = "failed"
                db.commit()
        except Exception:
            pass
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
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 25 MB limit.")

    # Upload to Cloudinary — non-fatal if it fails
    cloudinary_url = None
    try:
        cloudinary_url = upload_pdf_to_cloudinary(file_bytes, file.filename)
    except Exception as e:
        print(f"[Upload] Cloudinary storage skipped (non-fatal): {e}")
        cloudinary_url = f"local://{file.filename}"

    # Create DB record immediately so the user sees the document
    doc = Document(
        title=file.filename,
        cloudinary_url=cloudinary_url,
        owner_id=current_user.id,
        status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Kick off the staged background task
    background_tasks.add_task(process_document_background, file_bytes, doc.id, file.filename)

    return {"id": doc.id, "title": doc.title, "status": doc.status, "message": "Document is processing."}


@router.get("/")
def get_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "status": d.status,
            "cloudinary_url": d.cloudinary_url,
            "summary_short": d.summary_short,
            "summary_detailed": d.summary_detailed,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.get("/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {
        "id": doc.id,
        "title": doc.title,
        "status": doc.status,
        "cloudinary_url": doc.cloudinary_url,
        "summary_short": doc.summary_short,
        "summary_detailed": doc.summary_detailed,
        "created_at": doc.created_at,
    }


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

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

    if doc.cloudinary_url and doc.cloudinary_url.startswith("http"):
        delete_from_cloudinary(doc.cloudinary_url)

    return {"message": "Document deleted successfully."}
