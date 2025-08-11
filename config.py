"""
Configuration management for LineCook application.

This module centralizes all configuration settings and constants, providing
a single source of truth for application behavior.
"""

import logging
from pathlib import Path
from typing import Tuple

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Application constants
TARGET_SIZE: Tuple[int, int] = (1200, 1800)  # 4x6 inch at 300 DPI
TARGET_RATIOS: Tuple[float, float] = (4 / 6, 6 / 4)  # Standard shipping label ratios
DEFAULT_DPI: int = 300
MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB max file size
ALLOWED_EXTENSIONS: set[str] = {".pdf", ".jpg", ".jpeg", ".png"}
TEMP_DIR: Path = Path("tmp")
OUTPUT_DIR: Path = Path("test_outputs")

# Ensure directories exist
TEMP_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    All settings can be overridden via environment variables with the same name
    (case insensitive). The application will look for a .env file in the project root.
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'  # Ignore extra environment variables
    )
    
    # Required fields
    roboflow_api_key: str = Field(
        description="Roboflow API key for inference"
    )
    
    # Model configuration
    model_id: str = Field(
        default="shipping-label-k3hzg/4",
        description="Roboflow model ID for label detection"
    )
    confidence_thresh: float = Field(
        default=0.04,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for predictions"
    )
    
    # Print configuration
    print_command: str = Field(
        default="auto",
        description="Print command to use. 'auto' for system default, or custom command like 'lpr -P printer_name'"
    )
    print_enabled: bool = Field(
        default=True,
        description="Enable/disable printing functionality"
    )
    print_debug: bool = Field(
        default=False,
        description="Enable debug output for print operations"
    )
    
    # Logging configuration
    log_level: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Security configuration
    max_file_size: int = Field(
        default=MAX_FILE_SIZE,
        description="Maximum allowed file upload size in bytes"
    )
    
    # API configuration
    api_timeout: int = Field(
        default=30,
        description="API request timeout in seconds"
    )


def setup_logging(settings: Settings) -> logging.Logger:
    """
    Configure application logging based on settings.
    
    Args:
        settings: Application settings instance
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


# Global settings instance
settings = Settings()
logger = setup_logging(settings)