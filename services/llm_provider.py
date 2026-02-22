from openai import OpenAI
from config import GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY


PROVIDERS = [
    p
    for p in [
        {
            "name": "Groq",
            "api_key": GROQ_API_KEY,
            "base_url": "https://api.groq.com/openai/v1",
            "chat_model": "llama-3.3-70b-versatile",
            "analysis_model": "llama-3.3-70b-versatile",
        }
        if GROQ_API_KEY
        else None,
        {
            "name": "Gemini",
            "api_key": GEMINI_API_KEY,
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "chat_model": "gemini-2.0-flash",
            "analysis_model": "gemini-2.0-flash",
        }
        if GEMINI_API_KEY
        else None,
        {
            "name": "OpenAI",
            "api_key": OPENAI_API_KEY,
            "base_url": None,
            "chat_model": "gpt-4o-mini",
            "analysis_model": "gpt-3.5-turbo",
        }
        if OPENAI_API_KEY
        else None,
    ]
    if p
]


def get_client(provider: dict) -> OpenAI:
    kwargs = {"api_key": provider["api_key"]}
    if provider["base_url"]:
        kwargs["base_url"] = provider["base_url"]
    return OpenAI(**kwargs)
