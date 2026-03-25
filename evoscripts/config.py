"""Configuration management using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="EVOSCRIPTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Keys
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude")
    openai_api_key: str = Field(default="", description="OpenAI API key for GPT-4o Judge")

    # Model Configuration
    code_agent_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model for code generation",
    )
    judge_model: str = Field(
        default="gpt-4o",
        description="Model for evaluation/judging",
    )

    # Sampling Configuration
    taste_sample_size: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of samples for taste alignment phase",
    )
    evolution_sample_size: int = Field(
        default=30,
        ge=10,
        le=100,
        description="Number of samples per evolution iteration",
    )

    # Exit Conditions
    precision_threshold: float = Field(
        default=0.9,
        ge=0.5,
        le=1.0,
        description="Minimum precision to exit evolution loop",
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum evolution iterations before stopping",
    )

    # HITL Configuration
    hitl_interval: int = Field(
        default=2,
        ge=1,
        description="Ask for human confirmation every N iterations",
    )

    # Sandbox Configuration
    sandbox_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout in seconds for script execution",
    )


# Global settings instance
settings = Settings()
