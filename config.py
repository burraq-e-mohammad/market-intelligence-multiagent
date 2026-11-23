import os
from dotenv import load_dotenv

def get_config():
    """
    Dynamically reload environment variables from .env on every call.
    This guarantees any changes to API keys or providers take effect immediately
    without requiring a server restart.
    """
    load_dotenv(override=True)
    
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    
    # Auto-detect or sanitize provider
    if provider in ["mock", "gemini", "groq", "ollama"]:
        active_provider = provider
    elif gemini_key:
        active_provider = "gemini"
    elif groq_key:
        active_provider = "groq"
    else:
        active_provider = "mock"
        
    return {
        "PROVIDER": active_provider,
        "GEMINI_API_KEY": gemini_key,
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "GROQ_API_KEY": groq_key,
        "GROQ_MODEL": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3")
    }

# Initial module load properties
_cfg = get_config()
PROVIDER = _cfg["PROVIDER"]
GEMINI_API_KEY = _cfg["GEMINI_API_KEY"]
GEMINI_MODEL = _cfg["GEMINI_MODEL"]
GROQ_API_KEY = _cfg["GROQ_API_KEY"]
GROQ_MODEL = _cfg["GROQ_MODEL"]
OLLAMA_BASE_URL = _cfg["OLLAMA_BASE_URL"]
OLLAMA_MODEL = _cfg["OLLAMA_MODEL"]
