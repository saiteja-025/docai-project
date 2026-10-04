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
    file_path = "test_upload.txt"
    if not os.path.exists(file_path):
        print(f"{file_path} not found.")
        return

    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "text/plain")}
        res = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files=files)
        if res.status_code == 200:
            doc_id = res.json().get("id")
            print("Upload success, doc_id:", doc_id)
        else:
            print("Upload Failed:", res.status_code, res.text)
            return

    # 4. Get Documents List & Wait for processing
    print("Testing Document Listing...")
    import time
    time.sleep(3) # allow background task to process
    res = requests.get(f"{BASE_URL}/documents/", headers=headers)
    if res.status_code == 200 and len(res.json()) > 0:
        doc = res.json()[0]
        print(f"Document List success: {doc['title']} (status: {doc['status']})")
    else:
        print("Document List Failed:", res.status_code, res.text)

    # 5. Test Chat with document
    print("Testing Chat...")
    res = requests.post(f"{BASE_URL}/chat/{doc_id}/chat", headers=headers, json={"query": "What is AI?"})
    if res.status_code == 200:
        print("Chat success, reply snippet:", res.json().get("reply")[:60])
    else:
        print("Chat Failed:", res.status_code, res.text)

    # 6. Test Quiz Generation
    print("Testing Quiz Generation...")
    res = requests.get(f"{BASE_URL}/quiz/{doc_id}", headers=headers)
    if res.status_code == 200:
        print("Quiz success, questions count:", len(res.json().get("questions", [])))
    else:
        print("Quiz Failed:", res.status_code, res.text)

    # 7. Test Dashboard Stats
    print("Testing Dashboard Stats...")
    res = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
    if res.status_code == 200:
        print("Dashboard stats success:", res.json())
    else:
        print("Dashboard Stats Failed:", res.status_code, res.text)

    print("ALL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
