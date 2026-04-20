# 🧠 Document Intelligence Platform

> 🚀 AI-powered document analysis system using RAG (Retrieval-Augmented Generation)
> Transform PDFs into interactive knowledge with summaries, quizzes, and contextual chat.

---

## 🌟 Overview

The **Document Intelligence Platform** is a full-stack AI application that enables users to upload documents and interact with them using advanced language models.

It combines **FastAPI + React + LLMs + Vector Search** to deliver a production-ready SaaS experience.

---

## ✨ Key Features

* 📂 **Document Upload & Management**

  * Drag-and-drop PDF uploads
  * Background processing pipeline

* 🤖 **RAG-based AI Chat**

  * Context-aware responses grounded in documents
  * No hallucinations — answers strictly from uploaded files

* 📝 **Smart Summarization**

  * Short summaries
  * Detailed bullet-point insights

* 🧪 **AI Quiz Generator**

  * Auto-generated MCQs from documents
  * Interactive knowledge testing

* 🎨 **Premium UI/UX**

  * Dark/Light mode
  * Glassmorphism design
  * Smooth animations (Framer Motion)

---

## 🏗️ Tech Stack

### 🔹 Frontend

* React (Vite)
* TailwindCSS
* Framer Motion
* Lucide Icons

### 🔹 Backend

* FastAPI
* SQLAlchemy
* PostgreSQL

### 🔹 AI & ML

* Groq API (LLaMA / Mixtral)
* HuggingFace Embeddings
* RAG Architecture

### 🔹 Vector Database

* FAISS (local vector storage)

### 🔹 Storage

* Cloudinary (file storage)

---

## 🧠 System Architecture

```id="arch01"
User → React Frontend → FastAPI Backend → AI Models (Groq)
                                   ↓
                             FAISS Vector DB
                                   ↓
                             Context Retrieval
```

---

## ⚙️ Local Setup Guide

### 🔹 1. Clone Repository

```bash id="cmd01"
git clone https://github.com/saiteja-025/docai-project.git
cd docai-project
```

---

### 🔹 2. Backend Setup

```bash id="cmd02"
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

👉 Runs on: `http://127.0.0.1:8000`

---

### 🔹 3. Frontend Setup

```bash id="cmd03"
cd frontend
npm install
npm run dev
```

👉 Runs on: `http://localhost:5173`

---

### 🔹 4. Environment Variables

Create `.env` in backend:

```env id="env01"
GROQ_API_KEY=your_key
CLOUDINARY_URL=your_url
SECRET_KEY=your_secret
```

---

## 📸 Demo (Local)

👉 Run backend + frontend locally to explore:

* Document upload
* Chat with PDF
* AI summary generation
* Quiz creation

---

## 🚧 Deployment Note

Due to heavy AI dependencies (FAISS, embeddings, etc.),
deployment on free platforms is limited.

👉 Recommended approaches:

* Docker-based deployment
* Cloud platforms (AWS / GCP / Railway)

---

## 🔮 Future Enhancements

* 🌐 Deploy scalable vector DB (Pinecone)
* 📊 Analytics dashboard
* 📱 Mobile-friendly UI
* 🧠 Multi-document reasoning

---

## 📌 Highlights

✔ End-to-end AI SaaS architecture
✔ Real-world RAG implementation
✔ Clean UI + backend separation
✔ Production-ready structure

---

## 👨‍💻 Author

**Saiteja Kandagatla**
🔗 GitHub: https://github.com/saiteja-025

---

## ⭐ Support

If you found this project useful:

👉 Star the repo
👉 Share feedback
👉 Connect on LinkedIn

---
