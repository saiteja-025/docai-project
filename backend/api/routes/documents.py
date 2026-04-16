from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import User, Document
from backend.api.deps import get_current_user
from backend.services.cloudinary_service import upload_pdf_to_cloudinary
from backend.services.rag_service import process_and_store_document
from backend.services.generation_service import generate_summary

router = APIRouter()

def process_document_background(file_bytes: bytes, doc_id: int):
    from backend.db.session import SessionLocal
    db = SessionLocal()
    try:
        # Process and store in FAISS
        text = process_and_store_document(file_bytes, str(doc_id))
        
        # Generate summary
        summary = generate_summary(text)
        
        # Update db
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "ready"
            doc.summary_short = summary.get("short", "")
            doc.summary_detailed = summary.get("detailed", "")
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
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
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
    background_tasks.add_task(process_document_background, file_bytes, doc.id)
    
    return {"id": doc.id, "title": doc.title, "status": doc.status, "message": "Document is processing."}

@router.get("/")
def get_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
    return [{"id": d.id, "title": d.title, "status": d.status, "created_at": d.created_at} for d in docs]
