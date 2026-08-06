"""Document Detection / LLM 설정."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentSettings(BaseSettings):
    """Layout+OCR(+LLM) 파이프라인 설정."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Layout+OCR / vision_llm
    document_detection_engine: str = Field(default="paddle", alias="DOCUMENT_DETECTION_ENGINE")
    document_ocr_lang: str = Field(default="korean", alias="DOCUMENT_OCR_LANG")
    document_use_stub_fallback: bool = Field(default=True, alias="DOCUMENT_USE_STUB_FALLBACK")
    document_vision_max_pages: int = Field(default=5, alias="DOCUMENT_VISION_MAX_PAGES")
    document_vision_model: str = Field(default="", alias="DOCUMENT_VISION_MODEL")

    # Optional OpenAI-compatible LLM (polish / vision)
    document_llm_enabled: bool = Field(default=False, alias="DOCUMENT_LLM_ENABLED")
    document_llm_base_url: str = Field(default="https://api.openai.com/v1", alias="DOCUMENT_LLM_BASE_URL")
    document_llm_api_key: str = Field(default="", alias="DOCUMENT_LLM_API_KEY")
    document_llm_model: str = Field(default="gpt-4o-mini", alias="DOCUMENT_LLM_MODEL")
