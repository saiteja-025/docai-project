import os
from io import BytesIO
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
try:
    from langchain.chains import create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains.history_aware_retriever import create_history_aware_retriever
except ImportError:
    from langchain_classic.chains import create_retrieval_chain
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
    from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate
from backend.services.generation_service import get_llm
from backend.core.config import settings

# ---------------------------------------------------------------------------
# Embeddings — lazily initialised so the model is loaded only once, on first
# use, rather than at import time. The Docker build pre-caches the model, so
# this is instant inside the container even after restarts.
# ---------------------------------------------------------------------------
FAISS_STORE_PATH = "faiss_store"

_embeddings = None
_cached_vectorstore = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return (and lazily initialise) the shared HuggingFace embeddings model."""
    global _embeddings
    if _embeddings is None:
        print("[RAG] Loading embedding model 'all-MiniLM-L6-v2'...")
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("[RAG] Embedding model loaded.")
    return _embeddings


def get_vectorstore():
    global _cached_vectorstore
    if _cached_vectorstore is None:
        try:
            _cached_vectorstore = FAISS.load_local(
                FAISS_STORE_PATH, get_embeddings(), allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"[RAG] Could not load FAISS index from disk: {e}")
            return None
    return _cached_vectorstore


def invalidate_vectorstore_cache():
    global _cached_vectorstore
    _cached_vectorstore = None


# ---------------------------------------------------------------------------
# C2 Fix: Rebuild FAISS index from PostgreSQL on startup.
#
# Strategy (free, no paid services):
#   • When a document is processed, its extracted text is saved to the
#     `Document.content_text` column in PostgreSQL (see documents.py).
#   • On every container start the index is rebuilt from those stored texts.
#   • This means the FAISS index is always consistent with the DB, at the
#     cost of a one-time rebuild (~1–3 s per document) at startup.
# ---------------------------------------------------------------------------
def rebuild_faiss_index_from_db(db_session_factory=None):
    """Rebuild the in-memory FAISS index from all ready documents in the DB.

    Called once during application startup so that vector search works
    immediately after a container restart without any paid persistent disk.
    """
    from backend.db.models import Document

    if db_session_factory:
        db = db_session_factory()
    else:
        from backend.db.session import SessionLocal
        db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.status == "ready", Document.content_text.isnot(None))
            .all()
        )

        if not docs:
            print("[RAG] No indexed documents found in DB — FAISS index will be built on first upload.")
            return

        print(f"[RAG] Rebuilding FAISS index from {len(docs)} document(s) stored in DB...")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        all_chunks = []
        for doc in docs:
            chunks = text_splitter.create_documents(
                [doc.content_text],
                metadatas=[{"source": str(doc.id)}],
            )
            all_chunks.extend(chunks)

        if all_chunks:
            if not os.path.exists(FAISS_STORE_PATH):
                os.makedirs(FAISS_STORE_PATH)
            vectorstore = FAISS.from_documents(all_chunks, get_embeddings())
            vectorstore.save_local(FAISS_STORE_PATH)
            invalidate_vectorstore_cache()
            print(f"[RAG] FAISS index rebuilt with {len(all_chunks)} chunk(s) from {len(docs)} document(s).")

    except Exception as e:
        print(f"[RAG] Warning: Could not rebuild FAISS index on startup: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_text(file_bytes: bytes, filename: str) -> str:
    text = ""
    extension = filename.lower().split(".")[-1]

    try:
        if extension == "pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            for page in reader.pages:
                try:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                except Exception:
                    pass
        elif extension == "docx":
            from docx import Document
            doc = Document(BytesIO(file_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif extension == "txt":
            text = file_bytes.decode("utf-8")
    except Exception as e:
        print(f"[RAG] Error extracting text from {filename}: {e}")

    return text


def process_and_store_document(file_bytes: bytes, doc_id: str, filename: str) -> str:
    """Extract text, chunk it, and upsert into the shared FAISS vector store.

    Returns the raw extracted text so the caller can persist it to the DB.
    """
    text = extract_text(file_bytes, filename)

    if not text.strip():
        text = "No readable text could be extracted from this document."

    # Text chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.create_documents([text], metadatas=[{"source": doc_id}])

    # Upsert into FAISS vector store
    if not os.path.exists(FAISS_STORE_PATH):
        os.makedirs(FAISS_STORE_PATH)

    try:
        vectorstore = get_vectorstore()
        if vectorstore:
            vectorstore.add_documents(chunks)
            vectorstore.save_local(FAISS_STORE_PATH)
        else:
            raise Exception("No existing index — creating new one.")
    except Exception as e:
        print(f"[RAG] Creating new FAISS index: {e}")
        vectorstore = FAISS.from_documents(chunks, get_embeddings())
        vectorstore.save_local(FAISS_STORE_PATH)

    invalidate_vectorstore_cache()
    return text


# ---------------------------------------------------------------------------
# RAG chat
# ---------------------------------------------------------------------------
def chat_with_document(doc_id: str, query: str, chat_history: list = None) -> str:
    if not settings.GROQ_API_KEY:
        return (
            "AI chat is currently unavailable because GROQ_API_KEY is not configured. "
            "Please add your Groq API key in the environment variables and redeploy."
        )

    vectorstore = get_vectorstore()
    if not vectorstore:
        return (
            "The document knowledge base is not yet ready. "
            "Please wait a moment and try again — the index may still be rebuilding."
        )

    # Restrict retrieval to this specific document via metadata filter
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 5, "filter": {"source": doc_id}}
    )

    llm = get_llm()

    from langchain_core.prompts import MessagesPlaceholder

    system_prompt = (
        "You are an intelligent AI assistant helping the user understand a specific document they have uploaded. "
        "Answer their questions accurately using the provided context from the document. "
        "If the user asks a general question, reply helpfully, but always prioritise the document context. "
        "If you don't know the answer or the context doesn't contain it, say so clearly and politely.\n\n"
        "Context:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question which might reference context in the chat history, "
        "formulate a standalone question that can be understood without the chat history. "
        "Do NOT answer the question — just reformulate it if needed, otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    if chat_history is None:
        chat_history = []

    from langchain_core.messages import HumanMessage, AIMessage
    formatted_history = []
    for role, content in chat_history:
        if role == "user":
            formatted_history.append(HumanMessage(content=content))
        else:
            formatted_history.append(AIMessage(content=content))

    try:
        response = rag_chain.invoke({"input": query, "chat_history": formatted_history})
        return response["answer"]
    except Exception as e:
        print(f"[RAG] Chain execution error: {e}")
        return f"Error communicating with Groq AI service: {str(e)}"
