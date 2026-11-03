import os
import sys
import time
import threading
import uvicorn
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from backend.main import app
from backend.db.session import SessionLocal
from backend.db.models import User, Document

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8889
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def run_server():
    config = uvicorn.Config(app=app, host=SERVER_HOST, port=SERVER_PORT, log_level="error")
    server = uvicorn.Server(config)
    server.run()

def wait_for_port(host, port, timeout=30):
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False

def main():
    print("[1/3] Pre-seeding ready document and starting server...", flush=True)
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    if not wait_for_port(SERVER_HOST, SERVER_PORT):
        raise RuntimeError("Server failed to bind to port within timeout.")
    time.sleep(1)

    db = SessionLocal()
    # Create or get user
    user = db.query(User).filter(User.email == "targeted_tester@example.com").first()
    if not user:
        from backend.core.security import get_password_hash
        user = User(email="targeted_tester@example.com", hashed_password=get_password_hash("Pass12345!"))
        db.add(user)
        db.commit()
        db.refresh(user)

    # Ensure ready document exists
    doc = db.query(Document).filter(Document.owner_id == user.id).first()
    if not doc:
        doc = Document(
            title="targeted_audit_doc.pdf",
            cloudinary_url="mock_url",
            content_text="DocAI provides high precision RAG question answering, embeddings, and automated quizzes.",
            summary_short="DocAI provides high precision RAG question answering.",
            summary_detailed="• High precision RAG\n• HuggingFace Embeddings\n• FAISS vector indexing",
            status="ready",
            owner_id=user.id
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    db.close()

    print("[2/3] Launching Playwright to test Modal, Chat, and Quiz...", flush=True)
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Login
        page.goto(SERVER_URL)
        page.wait_for_timeout(1000)
        page.locator("form input").nth(0).fill("targeted_tester@example.com")
        page.locator("form input").nth(1).fill("Pass12345!")
        page.locator("button[type='submit']").click()
        page.wait_for_selector("text=Dashboard", timeout=8000)
        results["Login"] = "PASS"

        # Test 1: Documents Page & Summary Modal
        page.locator("a[href='/documents']").click()
        page.wait_for_selector("text=Documents", timeout=5000)
        page.wait_for_timeout(1000)

        summary_btn = page.locator("button[title*='Summary'], button[title*='Details']").first
        summary_btn.click()
        page.wait_for_timeout(1000)
        short_summary_visible = page.locator("h4:has-text('Short Summary')").is_visible()
        detailed_summary_visible = page.locator("h4:has-text('Detailed Insights')").is_visible()
        results["Summary_Modal"] = "PASS" if (short_summary_visible and detailed_summary_visible) else "FAIL"

        # Close modal
        page.locator("button:has-text('Close')").first.click()
        page.wait_for_timeout(500)

        # Test 2: AI Chat
        page.locator("a[href='/chat']").click()
        page.wait_for_selector("text=Knowledge Base", timeout=5000)
        page.wait_for_timeout(1000)

        # Click document in list
        page.locator("div.line-clamp-2:has-text('targeted_audit_doc')").first.click()
        page.wait_for_timeout(500)

        chat_input = page.locator("textarea").first
        chat_input.fill("What is DocAI?")
        page.locator("button:has(svg.lucide-send)").first.click()
        page.wait_for_timeout(3000)

        chat_bubble_visible = page.locator("div.chat-bubble, div.rounded-2xl").count() > 1
        results["AI_Chat"] = "PASS" if chat_bubble_visible else "FAIL"

        # Test 3: AI Quizzes
        page.locator("a[href='/quizzes']").click()
        page.wait_for_selector("text=Quiz Engine", timeout=5000)
        page.wait_for_timeout(1000)

        # Click document in quiz sidebar
        page.locator("div.line-clamp-2:has-text('targeted_audit_doc')").first.click()
        page.wait_for_timeout(500)

        # Click Hard difficulty
        page.locator("button:has-text('hard'), button:has-text('Hard')").first.click()
        page.wait_for_timeout(300)

        # Click Generate Quiz
        page.locator("button:has-text('Generate Quiz')").first.click()
        page.wait_for_timeout(4000)

        q1_present = page.locator("h4:has-text('Q1.')").is_visible()
        results["Quiz_Generation"] = "PASS" if q1_present else "FAIL"

        if q1_present:
            # Answer question 1
            page.locator("div.cursor-pointer:has-text('RAG-based')").first.click()
            page.wait_for_timeout(300)

            # Answer question 2
            page.locator("div.cursor-pointer:has-text('all-MiniLM')").first.click()
            page.wait_for_timeout(300)

            # Submit Quiz
            page.locator("button:has-text('Submit Quiz')").first.click()
            page.wait_for_timeout(1500)
            score_visible = page.locator("text=Quiz Completed!").is_visible() or page.locator("text=Total Score").is_visible()
            results["Quiz_Scoring"] = "PASS" if score_visible else "FAIL"

            retake_btn = page.locator("button:has-text('Retake This Quiz')").first
            retake_visible = retake_btn.is_visible()
            if retake_visible:
                retake_btn.click()
                page.wait_for_timeout(500)
            results["Quiz_Retake"] = "PASS" if retake_visible else "FAIL"

        browser.close()

    print("\n[3/3] RESULTS:")
    for k, v in results.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
