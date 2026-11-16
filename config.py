import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# LLM Configuration
# Options for PROVIDER: 'gemini', 'groq', 'ollama', 'mock'
PROVIDER = os.getenv("LLM_PROVIDER", "").lower()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Auto-detect provider if not explicitly specified
if not PROVIDER:
    if GEMINI_API_KEY:
        PROVIDER = "gemini"
    elif GROQ_API_KEY:
        PROVIDER = "groq"
    else:
        PROVIDER = "mock" # Out of the box fallback without crashing

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
