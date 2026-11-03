import json
import random
from langchain_groq import ChatGroq
from backend.core.config import settings

class MockLLM:
    def invoke(self, prompt: str):
        class MockResponse:
            content = "This is a mock response because GROQ_API_KEY is not configured. Please add your API key to use AI features natively."
        return MockResponse()

def get_llm(temperature=0.2):
    if not settings.GROQ_API_KEY:
        return MockLLM()
    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile", 
        temperature=temperature,
        max_tokens=2048,
    )

def generate_summary(text: str) -> dict:
    if not settings.GROQ_API_KEY:
        snippet = text[:300].strip().replace("\n", " ") if text else "Document uploaded."
        return {
            "short": f"Document preview: {snippet}..." if len(snippet) >= 300 else f"Document summary: {snippet}",
            "detailed": f"• Extracted text length: {len(text)} characters\n• Document preview: {snippet}\n• Add GROQ_API_KEY in Render environment settings to enable live LLM summaries.",
        }

    prompt = (
        "Summarize the following text in two formats: "
        "A short 2-sentence summary, and a detailed bulleted summary. "
        "Format output strictly as JSON with keys 'short' and 'detailed'.\n\n"
        f"Text: {text[:5000]}"
    )
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "short" in parsed and "detailed" in parsed:
            return parsed
        return {"short": "Summary generated.", "detailed": content}
    except Exception as e:
        print(f"Generation error: {e}")
        return {"short": "Document processed.", "detailed": text[:1000]}

def generate_mcqs(text: str, difficulty: str = "medium") -> str:
    if not settings.GROQ_API_KEY:
        return json.dumps([
            {
                "question": "What is the primary function of this document intelligence platform?",
                "options": [
                    "RAG-based AI search, summarization, and interactive quizzes",
                    "Photo editing and social networking",
                    "Video game streaming",
                    "Hardware diagnostics"
                ],
                "correct_answer": "RAG-based AI search, summarization, and interactive quizzes",
                "explanation": "DocAI leverages RAG, embeddings, and LLMs to interact with documents."
            },
            {
                "question": "Which embedding model is used for document vector representation?",
                "options": [
                    "all-MiniLM-L6-v2",
                    "ResNet-50",
                    "BERT-large-uncased-only",
                    "VGG-16"
                ],
                "correct_answer": "all-MiniLM-L6-v2",
                "explanation": "all-MiniLM-L6-v2 provides fast, lightweight 384-dimensional sentence embeddings."
            }
        ])
    try:
        llm = get_llm(temperature=0.8)
        seed = random.randint(1, 999999)
        prompt = f"""Generate 5 distinctly different and unique multiple-choice questions ({difficulty} difficulty) based strictly on the provided content. 
CRITICAL REQUIREMENT: To ensure variety across multiple requests, emphasize completely different facts, details, or sections of the content. Do not just ask about the main topic. 
Do NOT mention "the provided text", "the document", "the pdf", or "the content" in your questions. Formulate questions directly about the subject matter.
Randomization factor: {seed} (use this to entirely shift your selection of questions).
Return PURELY a JSON array of objects with keys: 'question', 'options' (array of 4 strings), 'correct_answer', and 'explanation'. Do not include markdown formatting or additional text.

Content: {text[:5000]}"""
        response = llm.invoke(prompt)
        text_content = response.content
        if "```" in text_content:
            text_content = text_content.split("```")[1]
            if text_content.startswith("json"):
                text_content = text_content[4:]
        return text_content.strip()
    except Exception as e:
        print(f"MCQ Generation error: {e}")
        return json.dumps([])
