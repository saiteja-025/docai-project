import os
import sys
import json
import pytest
from io import BytesIO
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.db.session import Base, get_db
from backend.services.rag_service import extract_text, process_and_store_document, rebuild_faiss_index_from_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup an isolated test database
TEST_DB_URL = "sqlite:///./test_audit.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("test_audit.db"):
        try:
            os.remove("test_audit.db")
        except Exception:
            pass

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

# Helper: Valid minimal PDF bytes
VALID_PDF_BYTES = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 73 >> stream
BT
/F1 12 Tf
72 712 Td
(DocAI: Artificial Intelligence and RAG Document Systems) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000318 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
440
%%EOF"""


# ============================================================================
# 1. AUTHENTICATION & SECURITY TESTS
# ============================================================================

def test_user_signup_success(client):
    res = client.post("/api/v1/auth/signup", json={"email": "alice@test.com", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "alice@test.com"
    assert "id" in data

def test_user_signup_duplicate_email(client):
    res = client.post("/api/v1/auth/signup", json={"email": "alice@test.com", "password": "password123"})
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()

def test_user_signup_invalid_email(client):
    res = client.post("/api/v1/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert res.status_code == 422

def test_user_login_success(client):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_user_login_wrong_password(client):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert res.status_code == 400
    assert "incorrect email or password" in res.json()["detail"].lower()

def test_user_login_nonexistent_user(client):
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert res.status_code == 400
    assert "incorrect email or password" in res.json()["detail"].lower()

def test_get_current_user_me(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]
    
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "alice@test.com"

def test_protected_route_without_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

def test_protected_route_with_invalid_token(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert res.status_code == 401


# ============================================================================
# 2. DOCUMENT MANAGEMENT & VALIDATION TESTS
# ============================================================================

def test_upload_invalid_extension(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]
    
    files = {"file": ("malicious.exe", b"binarycontent", "application/octet-stream")}
    res = client.post("/api/v1/documents/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 400
    assert "only pdf, docx, and txt" in res.json()["detail"].lower()

def test_upload_file_exceeding_size_limit(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]
    
    # 26 MB file
    oversized = b"A" * (26 * 1024 * 1024)
    files = {"file": ("large_doc.pdf", oversized, "application/pdf")}
    res = client.post("/api/v1/documents/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 400
    assert "exceeds" in res.json()["detail"].lower()

def test_upload_pdf_success_and_sync_processing(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    files = {"file": ("ai_overview.pdf", VALID_PDF_BYTES, "application/pdf")}
    res = client.post("/api/v1/documents/upload", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert res.status_code == 200
    doc_data = res.json()
    assert doc_data["title"] == "ai_overview.pdf"
    doc_id = doc_data["id"]

    # Manually execute background task processing to test RAG pipeline immediately
    from backend.api.routes.documents import process_document_background
    process_document_background(VALID_PDF_BYTES, doc_id, "ai_overview.pdf", db_session_factory=TestingSessionLocal)

    # Verify document is marked ready and has extracted content
    detail_res = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["status"] == "ready"
    assert detail["title"] == "ai_overview.pdf"
    assert detail["summary_short"] is not None

def test_document_listing(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    res = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1
    assert "title" in docs[0]
    assert "status" in docs[0]
    assert "cloudinary_url" in docs[0]

def test_tenant_data_isolation(client):
    # Register Bob
    client.post("/api/v1/auth/signup", json={"email": "bob@test.com", "password": "password123"})
    bob_login = client.post(
        "/api/v1/auth/login",
        data={"username": "bob@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    bob_token = bob_login.json()["access_token"]

    # Bob lists documents - should be empty initially
    res = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {bob_token}"})
    assert res.status_code == 200
    assert len(res.json()) == 0

    # Bob tries to access Alice's document (ID 1)
    res = client.get("/api/v1/documents/1", headers={"Authorization": f"Bearer {bob_token}"})
    assert res.status_code == 404

    # Bob tries to delete Alice's document (ID 1)
    res = client.delete("/api/v1/documents/1", headers={"Authorization": f"Bearer {bob_token}"})
    assert res.status_code == 404


# ============================================================================
# 3. AI DOCUMENT CHAT & RAG TESTS
# ============================================================================

def test_chat_with_document(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    # Get Alice's document ID
    docs = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"}).json()
    doc_id = docs[0]["id"]

    # Send a query
    chat_res = client.post(
        f"/api/v1/chat/{doc_id}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "What is this document about?"}
    )
    assert chat_res.status_code == 200
    assert "reply" in chat_res.json()
    assert len(chat_res.json()["reply"]) > 0

    # Verify chat history is recorded
    hist_res = client.get(f"/api/v1/chat/{doc_id}/history", headers={"Authorization": f"Bearer {token}"})
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "ai"

def test_chat_nonexistent_document(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    res = client.post(
        "/api/v1/chat/99999/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Hello"}
    )
    assert res.status_code == 404


# ============================================================================
# 4. AI QUIZ GENERATION & SUBMISSION TESTS
# ============================================================================

def test_quiz_generation(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    docs = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"}).json()
    doc_id = docs[0]["id"]

    quiz_res = client.get(f"/api/v1/quiz/{doc_id}?difficulty=medium", headers={"Authorization": f"Bearer {token}"})
    assert quiz_res.status_code == 200
    questions = quiz_res.json().get("questions", [])
    assert len(questions) > 0
    q1 = questions[0]
    assert "question" in q1
    assert "options" in q1
    assert "correct_answer" in q1

def test_quiz_submission_and_scoring(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    submit_payload = {
        "quiz_id": 0,
        "score": 85.0,
        "answers_json": json.dumps({"0": "Option A", "1": "Option B"})
    }
    res = client.post("/api/v1/quiz/submit", headers={"Authorization": f"Bearer {token}"}, json=submit_payload)
    assert res.status_code == 200
    assert "successfully" in res.json()["message"].lower()


# ============================================================================
# 5. DASHBOARD STATISTICS TESTS
# ============================================================================

def test_dashboard_stats(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    res = client.get("/api/v1/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    stats = res.json()
    assert "doc_count" in stats
    assert stats["doc_count"] >= 1
    assert "chat_count" in stats
    assert "avg_score" in stats
    assert "activity" in stats
    assert len(stats["activity"]) == 7


# ============================================================================
# 6. DOCUMENT DELETION & CASCADE TESTS
# ============================================================================

def test_delete_document_cascade(client):
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@test.com", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]

    docs = client.get("/api/v1/documents/", headers={"Authorization": f"Bearer {token}"}).json()
    doc_id = docs[0]["id"]

    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200

    # Ensure document is gone
    check_res = client.get(f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert check_res.status_code == 404


# ============================================================================
# 7. ROUTING & SPA FALLBACK SAFETY TESTS
# ============================================================================

def test_unknown_api_route_returns_404_json(client):
    res = client.get("/api/v1/unknown_endpoint")
    assert res.status_code == 404
    assert res.json()["detail"] == "API route not found"


# ============================================================================
# 8. FAISS PERSISTENCE & DB REBUILD TEST
# ============================================================================

def test_faiss_rebuild_persistence(client):
    import shutil
    from backend.db.models import Document, User
    from backend.services.rag_service import get_vectorstore, invalidate_vectorstore_cache, FAISS_STORE_PATH

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "alice@test.com").first()
    if not user:
        user = User(email="alice@test.com", hashed_password="hashedpassword")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create document with content_text
    doc = Document(
        title="faiss_test_doc.txt",
        cloudinary_url="mock_url",
        content_text="DocAI uses FAISS and embeddings for instant retrieval across document pages.",
        status="ready",
        owner_id=user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    db.close()

    # Simulate container restart: remove local faiss_store and cache
    invalidate_vectorstore_cache()
    if os.path.exists(FAISS_STORE_PATH):
        try:
            shutil.rmtree(FAISS_STORE_PATH)
        except Exception:
            pass

    # Call rebuild from database
    rebuild_faiss_index_from_db(db_session_factory=TestingSessionLocal)

    # Verify vectorstore is re-established and searchable
    vectorstore = get_vectorstore()
    assert vectorstore is not None
    results = vectorstore.similarity_search("FAISS retrieval", k=1)
    assert len(results) > 0
    assert "DocAI uses FAISS" in results[0].page_content
