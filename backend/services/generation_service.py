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
        # Parse logic would go here, returning mock/raw for now
        # In a full app, we'd use JsonOutputParser
        return {"raw": response.content}
    except Exception as e:
        print(f"Generation error: {e}")
        return {"short": "Error generating summary.", "detailed": str(e)}

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
        prompt = f"""Generate 5 distinctly different and unique multiple-choice questions ({difficulty} difficulty) based on the provided text. 
CRITICAL REQUIREMENT: To ensure variety across multiple requests, emphasize completely different facts, details, or sections of the text. Do not just ask about the main topic. 
Randomization factor: {seed} (use this to entirely shift your selection of questions).
Return PURELY a JSON array of objects with keys: 'question', 'options' (array of 4 strings), 'correct_answer', and 'explanation'. Do not include markdown formatting or additional text.

Text: {text[:5000]}"""
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
