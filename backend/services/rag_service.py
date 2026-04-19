import os
import tempfile
from io import BytesIO
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from backend.services.generation_service import get_llm
from backend.core.config import settings

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
FAISS_STORE_PATH = "faiss_store"

_cached_vectorstore = None

def get_vectorstore():
    global _cached_vectorstore
    if _cached_vectorstore is None:
        try:
            _cached_vectorstore = FAISS.load_local(FAISS_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"Error loading FAISS index: {e}")
            return None
    return _cached_vectorstore

def invalidate_vectorstore_cache():
    global _cached_vectorstore
    _cached_vectorstore = None

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
            text = file_bytes.decode('utf-8')
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        
    return text

def process_and_store_document(file_bytes: bytes, doc_id: str, filename: str):
    text = extract_text(file_bytes, filename)
    
    if not text.strip():
        text = "No readable text could be extracted from this document."
        
    # Text chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.create_documents([text], metadatas=[{"source": doc_id}])
    
    # Add to FAISS Vector Store
    if not os.path.exists(FAISS_STORE_PATH):
        os.makedirs(FAISS_STORE_PATH)

    try:
        # Load existing index if present
        vectorstore = get_vectorstore()
        if vectorstore:
            vectorstore.add_documents(chunks)
            vectorstore.save_local(FAISS_STORE_PATH)
        else:
            raise Exception("No existing index found, creating new one")
    except Exception as e:
        print(f"Creating new FAISS index: {e}")
        vectorstore = FAISS.from_documents(chunks, embeddings)
        vectorstore.save_local(FAISS_STORE_PATH)
        
    invalidate_vectorstore_cache()
    return text

def chat_with_document(doc_id: str, query: str, chat_history: list = None) -> str:
    if not settings.GROQ_API_KEY:
        return "I am currently running in mock mode. Please add your GROQ API key to environment variables to chat intelligently with this document."

    vectorstore = get_vectorstore()
    if not vectorstore:
        return "Knowledge base configuration is missing or index not found."
    
    # Create retriever with metadata filter to restrict to this document
    def filter_func(metadata):
        return metadata.get("source") == doc_id
        
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 5, "filter": {"source": doc_id}} if hasattr(vectorstore, "_similarity_search_with_relevance_scores") else {"k": 5} 
    )
    # Note: FAISS in latest langchain-community accepts `filter` dict.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {"source": doc_id}})
    
    llm = get_llm()
    
    from langchain_core.prompts import MessagesPlaceholder
    system_prompt = (
        "You are an intelligent AI assistant helping the user understand a specific PDF document they have uploaded and selected. "
        "Your task is to answer their questions accurately using the provided context from their document. "
        "If they are asking a general question, you can reply normally, but always try to prioritize the provided document context. "
        "If you don't know the answer or the context doesn't have it, say so clearly, but be polite and helpful. "
        "\n\nContext:\n{context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    
    # Simple history-aware parsing mechanism
    from langchain.chains.history_aware_retriever import create_history_aware_retriever
    
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])
    
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    # Format chat_history for Langchain
    if chat_history is None:
        chat_history = []
        
    formatted_history = []
    from langchain_core.messages import HumanMessage, AIMessage
    for role, content in chat_history:
        if role == "user":
            formatted_history.append(HumanMessage(content=content))
        else:
            formatted_history.append(AIMessage(content=content))
            
    response = rag_chain.invoke({"input": query, "chat_history": formatted_history})
    return response["answer"]
