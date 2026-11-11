import json
import random
from langchain_groq import ChatGroq
from backend.core.config import settings

def get_llm(temperature=0.2):
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured. Please provide a valid Groq API key.")
    return ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=temperature,
        max_tokens=2048,
    )

def _extract_json_from_response(content: str) -> str:
    """Strip markdown code fences and return raw JSON string."""
    if "```" in content:
        parts = content.split("```")
        # The fenced block is usually parts[1]
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()

def generate_summary(text: str) -> dict:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured. Cannot generate live LLM summary.")

    prompt = (
        "Summarize the following text in two formats: "
        "A short 2-sentence summary, and a detailed bulleted summary. "
        "Format output strictly as JSON with keys 'short' and 'detailed'.\n\n"
        f"Text: {text[:5000]}"
    )
    llm = get_llm()
    response = llm.invoke(prompt)
    content = _extract_json_from_response(response.content)

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "short" in parsed and "detailed" in parsed:
            return parsed
        return {"short": "Summary generated.", "detailed": str(parsed)}
    except (json.JSONDecodeError, ValueError):
        # LLM returned plain text — wrap gracefully so the document still becomes "ready"
        short = content[:300] if content else "Summary generated."
        return {"short": short, "detailed": content}

def generate_mcqs(text: str, difficulty: str = "medium") -> str:
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured. Cannot generate live LLM quiz.")

    llm = get_llm(temperature=0.8)
    seed = random.randint(1, 999999)
    prompt = f"""Generate 5 distinctly different and unique multiple-choice questions ({difficulty} difficulty) based strictly on the provided content. 
CRITICAL REQUIREMENT: To ensure variety across multiple requests, emphasize completely different facts, details, or sections of the content. Do not just ask about the main topic. 
Do NOT mention "the provided text", "the document", "the pdf", or "the content" in your questions. Formulate questions directly about the subject matter.
Randomization factor: {seed} (use this to entirely shift your selection of questions).
Return PURELY a JSON array of objects with keys: 'question', 'options' (array of 4 strings), 'correct_answer', and 'explanation'. Do not include markdown formatting or additional text.

Content: {text[:5000]}"""
    response = llm.invoke(prompt)
    return _extract_json_from_response(response.content)
