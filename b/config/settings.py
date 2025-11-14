from langchain_groq import ChatGroq # type: ignore
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set in environment variables!")

# Model configuration
LLM_MODEL = "llama-3.3-70b-versatile"

# Lazy LLM initialization (optional caching)
def get_llm():
    if not hasattr(get_llm, "_llm"):
        get_llm._llm = ChatGroq(
            model=LLM_MODEL,
            temperature=0.0,
            groq_api_key=GROQ_API_KEY,
        )
    return get_llm._llm

MAX_RETRIES = 2
