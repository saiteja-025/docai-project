import requests
import os

BASE_URL = "http://localhost:8000/api/v1"

def run_tests():
    print("starting test...")
    # 1. Register User
    print("Testing Registration...")
    res = requests.post(f"{BASE_URL}/auth/signup", json={"email": "test456@test.com", "password": "password123"})
    if res.status_code == 200:
        print("Registration success")
    elif res.status_code == 400 and "exists" in res.text:
       print("User already exists")
    else:
        print("Registration Failed:", res.text)
        return

    # 2. Login User
    print("Testing Login...")
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": "test456@test.com", "password": "password123"})
    if res.status_code == 200:
        token = res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print("Login success, token acquired")
    else:
        print("Login Failed:", res.text)
        return

    # 3. Upload File
    print("Testing File Upload...")
    file_path = "test.pdf"
    if not os.path.exists(file_path):
        print(f"{file_path} not found.")
        return

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        res = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files=files)
        if res.status_code == 200:
            doc_id = res.json().get("id")
            print("Upload success, doc_id:", doc_id)
        else:
            print("Upload Failed:", res.status_code, res.text)
            return

    # 4. Get Summary
    print("Testing Summarization...")
    res = requests.post(f"{BASE_URL}/chat/summarize/{doc_id}", headers=headers)
    if res.status_code == 200:
        print("Summarization success:", res.json().get("summary")[:50], "...")
    else:
        print("Summarization Failed:", res.status_code, res.text)

if __name__ == "__main__":
    run_tests()
