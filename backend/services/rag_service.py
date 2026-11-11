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
    try:
        from langchain_classic.chains import create_retrieval_chain
        from langchain_classic.chains.combine_documents import create_stuff_documents_chain
        from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
    except ImportError:
        create_retrieval_chain = None
        create_stuff_documents_chain = None
        create_history_aware_retriever = None

from langchain_core.prompts import ChatPromptTemplate
from backend.services.generation_service import get_llm
from backend.core.config import settings

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
FAISS_STORE_PATH = "faiss_store"
_embeddings = None
_cached_vectorstore = None


def get_embeddings() -> HuggingFaceEmbeddings:
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
# C2: Rebuild FAISS index from PostgreSQL on startup
# ---------------------------------------------------------------------------
def rebuild_faiss_index_from_db(db_session_factory=None):
    """Rebuild the in-memory FAISS index from all ready documents in the DB."""
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
            chunk_size=1000, chunk_overlap=200, length_function=len
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

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, length_function=len
    )
    chunks = text_splitter.create_documents([text], metadatas=[{"source": doc_id}])

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
# Direct LLM chat using raw content_text (fallback when FAISS is unavailable)
# ---------------------------------------------------------------------------
def _chat_with_text_directly(doc_text: str, query: str, chat_history: list = None) -> str:
    """Answer a question directly from the raw document text using Groq LLM.

    Used as a fallback when the FAISS vector index is not yet built or empty
    for this specific document. Sends the first 6000 chars of the document as
    context to the LLM — no vector retrieval needed.
    """
    llm = get_llm()
    context = doc_text[:6000] if doc_text else ""

    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    history_msgs = []
    if chat_history:
        for role, content in (chat_history or []):
            if role == "user":
                history_msgs.append(HumanMessage(content=content))
            else:
                history_msgs.append(AIMessage(content=content))

    system = SystemMessage(content=(
        "You are an intelligent AI assistant. The user has uploaded a document and wants to ask questions about it. "
        "Answer accurately based ONLY on the document context provided below. "
        "If the answer is not in the document, say so politely.\n\n"
        f"Document Context:\n{context}"
    ))

    messages = [system] + history_msgs + [HumanMessage(content=query)]
    response = llm.invoke(messages)
    return response.content


# ---------------------------------------------------------------------------
# RAG chat — tries FAISS first, falls back to raw text
# ---------------------------------------------------------------------------
def chat_with_document(doc_id: str, query: str, chat_history: list = None,
                        doc_content_text: str = None) -> str:
    """Answer a question about a document.

    Strategy:
    1. Try FAISS vector retrieval (best quality, context-specific).
    2. If FAISS has no results for this doc, fall back to direct LLM with raw text.
    3. If Groq is not configured, return a clear error message.
    """
    if not settings.GROQ_API_KEY:
        return (
            "AI chat is currently unavailable because GROQ_API_KEY is not configured. "
            "Please add your Groq API key in Render environment variables."
        )

    # --- Try FAISS retrieval first ---
    faiss_answer = None
    vectorstore = get_vectorstore()

    if vectorstore and create_retrieval_chain is not None:
        try:
            from langchain_core.prompts import MessagesPlaceholder

            retriever = vectorstore.as_retriever(
                search_kwargs={"k": 5, "filter": {"source": doc_id}}
            )

            # Quick check: does this doc have any indexed chunks?
            test_docs = retriever.invoke(query)
            if test_docs:
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

                contextualize_q_prompt = ChatPromptTemplate.from_messages([
                    ("system",
                     "Given a chat history and the latest user question, formulate a standalone question. "
                     "Do NOT answer — just reformulate if needed, otherwise return as-is."),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                ])

                llm = get_llm()
                history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
                question_answer_chain = create_stuff_documents_chain(llm, prompt)
                rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

                from langchain_core.messages import HumanMessage, AIMessage
                formatted_history = []
                for role, content in (chat_history or []):
                    if role == "user":
                        formatted_history.append(HumanMessage(content=content))
                    else:
                        formatted_history.append(AIMessage(content=content))

                response = rag_chain.invoke({"input": query, "chat_history": formatted_history})
                faiss_answer = response.get("answer", "")
        except Exception as e:
            print(f"[RAG] FAISS retrieval error (will fallback to direct LLM): {e}")

    if faiss_answer:
        return faiss_answer

    # --- Fallback: direct LLM with raw text ---
    if doc_content_text:
        print(f"[RAG] FAISS unavailable for doc {doc_id} — using direct LLM fallback.")
        try:
            return _chat_with_text_directly(doc_content_text, query, chat_history)
        except Exception as e:
            print(f"[RAG] Direct LLM fallback also failed: {e}")
            return f"Sorry, I encountered an error while answering your question: {e}"

    return (
        "The document knowledge base is not yet ready for this document. "
        "Please wait a moment and try again — the index may still be building."
    )
