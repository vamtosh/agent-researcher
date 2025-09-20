import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str
    deep_research_model: str = "gpt-5"
    synthesis_model: str = "gpt-5-mini"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # TCS Competitors List
    tcs_competitors: List[str] = [
        "Accenture",
        "IBM",
        "Infosys",
        "Cognizant",
        "Capgemini",
        "Wipro",
        "HCLTech",
        "Deloitte"
    ]

    # Research Configuration
    max_research_age_days: int = 60  # 2 months
    min_sources_per_competitor: int = 3
    max_research_timeout_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()