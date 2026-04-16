import os
import tempfile
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from backend.services.generation_service import get_llm

# Initialize Embeddings once
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
FAISS_STORE_PATH = "./faiss_store"

def extract_text_from_pdf(file_bytes: bytes) -> str:
    from io import BytesIO
    try:
        reader = PdfReader(BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            try:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            except Exception:
                pass
        return text
    except Exception as e:
        print(f"PyPDF2 error: {e}")
        return ""

def process_and_store_document(file_bytes: bytes, doc_id: str):
    text = extract_text_from_pdf(file_bytes)
    
    if not text.strip():
        text = "No readable text could be extracted from this document."
        
    # Text chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.create_documents([text], metadatas=[{"source": doc_id}])
    
    # Create or update FAISS Index
    if os.path.exists(FAISS_STORE_PATH):
        vectorstore = FAISS.load_local(FAISS_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
        vectorstore.add_documents(chunks)
    else:
        vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save local FAISS index
    if not os.path.exists(FAISS_STORE_PATH):
        os.makedirs(FAISS_STORE_PATH)
    vectorstore.save_local(FAISS_STORE_PATH)
    return text

def chat_with_document(doc_id: str, query: str) -> str:
    from backend.core.config import settings
    if not settings.GROQ_API_KEY:
        return "I am currently running in mock mode. Please add your GROQ API key to environment variables to chat intelligently with this document."

    if not os.path.exists(FAISS_STORE_PATH):
        return "Knowledge base not found. Please upload a document first."
        
    vectorstore = FAISS.load_local(FAISS_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
    
    # Create retriever with metadata filter to restrict to this document
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5, "filter": {"source": doc_id}})
    
    llm = get_llm()
    system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, say that you don't know."
        "\n\nContext: {context}"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    response = rag_chain.invoke({"input": query})
    return response["answer"]
