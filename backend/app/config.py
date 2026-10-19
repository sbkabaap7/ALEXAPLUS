from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', env_prefix='GUESTGUARD_')
    data_dir: Path = Path('data')
    model_dir: Path = Path('models')
    base_url: str = 'http://127.0.0.1:8000'
    session_seconds: int = 3600
    pin_seconds: int = 300
    cookie_secure: bool = False
    voice_threshold: float = 0.72
    voice_margin: float = 0.08
    llm_base_url: str = 'https://api.openai.com/v1'
    llm_api_key: str = ''
    llm_model: str = 'gpt-4.1-mini'
    ollama_base_url: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'qwen3:4b-instruct'
    stt_model: str = 'tiny.en'


settings = Settings()
