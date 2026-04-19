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
    prompt = f"Summarize the following text in two formats: A short 2-sentence summary, and a detailed bulleted summary. Format output as JSON with keys 'short' and 'detailed'.\n\nText: {text[:5000]}"
    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        import json
        parsed = json.loads(content.strip())
        return parsed
    except Exception as e:
        print(f"Generation error: {e}")
        return {"short": "Summary generated.", "detailed": text[:5000]}

def generate_mcqs(text: str, difficulty: str = "medium") -> str:
    if not settings.GROQ_API_KEY:
        import json
        return json.dumps([{
            "question": "This is a placeholder question because GROQ API key is missing. What is 2 + 2?",
            "options": ["1", "2", "3", "4"],
            "correct_answer": "4",
        }])
    try:
        import random
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
        # Ensure it returns the JSON array part
        if "```json" in text_content:
            text_content = text_content.split("```json")[-1].split("```")[0].strip()
        return text_content
    except Exception as e:
        print(f"MCQ Generation error: {e}")
        import json
        return json.dumps([])
