import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 경로 명시적 지정
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# LLM API 키 (무료 → Groq, Gemini / 유료 → OpenAI)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# OpenDart API 키 (https://opendart.fss.or.kr 에서 발급)
DART_API_KEY = os.getenv("DART_API_KEY", "")

# 시작 시 API 키 검증
def validate_config():
    """필수 API 키가 하나 이상 설정되었는지 확인"""
    llm_keys = [GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY]
    if not any(llm_keys):
        print("[경고] LLM API 키가 설정되지 않았습니다. AI 기능이 작동하지 않습니다.")
        print("  GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY 중 하나를 .env에 설정하세요.")
    if not DART_API_KEY:
        print("[참고] DART_API_KEY가 설정되지 않았습니다. 공시 기능이 제한됩니다.")

validate_config()
