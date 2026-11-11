from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db.models import User, Document, ChatSession, ChatMessage
from backend.api.deps import get_current_user
from backend.services.rag_service import chat_with_document

router = APIRouter()


class ChatRequest(BaseModel):
    query: str


@router.post("/{doc_id}/chat")
def chat_document(
    doc_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    if doc.status not in ("ready",):
        raise HTTPException(
            status_code=400,
            detail="Document is still processing. Please wait until status is 'ready'."
        )

    # Get or create chat session
    chat_session = db.query(ChatSession).filter(
        ChatSession.document_id == doc.id,
        ChatSession.user_id == current_user.id
    ).first()
    if not chat_session:
        chat_session = ChatSession(user_id=current_user.id, document_id=doc.id)
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

    # Fetch existing chat history for context
    history_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == chat_session.id
    ).order_by(ChatMessage.created_at.asc()).all()
    chat_history = [(m.role, m.content) for m in history_messages]

    # Save user message first
    user_msg = ChatMessage(session_id=chat_session.id, role="user", content=request.query)
    db.add(user_msg)
    db.commit()

    # Get AI response — passes raw content_text so FAISS fallback works
    ai_response_text = chat_with_document(
        doc_id=str(doc_id),
        query=request.query,
        chat_history=chat_history,
        doc_content_text=doc.content_text,  # Fallback when FAISS index not yet built
    )

    # Save AI response
    ai_msg = ChatMessage(session_id=chat_session.id, role="ai", content=ai_response_text)
    db.add(ai_msg)
    db.commit()

    return {"reply": ai_response_text}


@router.get("/{doc_id}/history")
def get_chat_history(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat_session = db.query(ChatSession).filter(
        ChatSession.document_id == doc_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not chat_session:
        return []

    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == chat_session.id
    ).order_by(ChatMessage.created_at.asc()).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]
