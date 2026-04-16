# Document Intelligence Platform 🧠

A production-ready SaaS built with React, FastAPI, Groq (LLaMA/Mixtral), huggingface embeddings, and FAISS for RAG document interaction. This platform allows you to upload PDFs, generate short and detailed summaries, take AI-generated quizzes, and chat with your files.

## 🚀 Key Features
- **Document Management**: Drag and drop PDF uploads with background processing.
- **RAG Chat System**: Context-aware chatting grounded purely in uploaded documents.
- **Smart Summarization**: Multi-format summaries (brief + bulleted detail).
- **AI Quizzes**: Auto-generate MCQs and test your knowledge.
- **Premium UX**: Framer Motion animations, Lucide icons, Dark/Light modes, Glassmorphism.

## 🏗 Tech Stack
- **Frontend**: Vite + React, TailwindCSS v4, Framer Motion
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Vector DB**: FAISS (Local filesystem)
- **AI Models**: Groq API (Inference), HuggingFace `sentence-transformers` (Embeddings)
- **File Storage**: Cloudinary

---

## 🛠 Local Setup Instructions

### 1. Backend Setup
1. Open terminal in the `backend/` directory.
2. Create virtualenv: `python -m venv venv`
3. Activate virtualenv: 
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Setup database: Run `docker-compose up -d` from root to start PostgreSQL.
6. Configure ENV: Copy `.env.example` to `.env` and fill:
   - `GROQ_API_KEY`
   - `CLOUDINARY_URL`
7. Start Server: `uvicorn main:app --reload` (Runs on port 8000)

### 2. Frontend Setup
1. Open terminal in the `frontend/` directory.
2. Install NodeJS if you haven't.
3. Install dependencies: `npm install`
4. Create `frontend/.env` and add: `VITE_API_BASE_URL=http://localhost:8000`
5. Start app: `npm run dev` (Runs on port 5173)

---

## 🌎 Deployment Guide (Free Tier)

### Frontend (Vercel)
1. Push this repository to GitHub.
2. Import the project in Vercel.
3. Set the Root Directory to `frontend`.
4. Framework Preset will auto-detect Vite. Add Environment Variable `VITE_API_BASE_URL` pointing to your Render server.

### Database (Render or Neon.tech)
1. Provision a free PostgreSQL database.
2. Note the connection string.

### File Storage (Cloudinary)
1. Create a free Cloudinary account.
2. Get your `CLOUDINARY_URL`.

### Backend (Render & Background tasks)
1. Create a new Web Service on Render, connect your GitHub.
2. Set Root Directory to `backend`.
3. Set Environment to Python 3.
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables: `DATABASE_URL`, `GROQ_API_KEY`, `CLOUDINARY_URL`, `SECRET_KEY`.

> **Note**: Render's free tier has an ephemeral disk. FAISS stores currently rely on local storage, meaning vector embeddings will clear on backend restart. For scale, connect a managed VectorDB (like Pinecone) or attach a persistent Render disk (paid).
