"""
Type definitions and result types for LineCook.

This module provides type-safe result handling patterns to improve
error handling and reduce complex return signatures.
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, Union, Optional, Dict, Any


T = TypeVar('T')
E = TypeVar('E')


@dataclass
class Ok(Generic[T]):
    """Represents a successful result."""
    value: T
    
    def is_ok(self) -> bool:
        return True
    
    def is_err(self) -> bool:
        return False
    
    def unwrap(self) -> T:
        return self.value
    
    def unwrap_or(self, default: T) -> T:
        return self.value


@dataclass
class Err(Generic[E]):
    """Represents an error result."""
    error: E
    
    def is_ok(self) -> bool:
        return False
    
    def is_err(self) -> bool:
        return True
    
    def unwrap(self) -> None:
        raise ValueError(f"Called unwrap on Err: {self.error}")
    
    def unwrap_or(self, default: T) -> T:
        return default


Result = Union[Ok[T], Err[E]]


@dataclass
class ProcessedLabel:
    """Result of successful label processing."""
    cropped_image: Any  # PIL.Image.Image
    temp_file_path: str
    prediction: Dict[str, Any]
    confidence: float


@dataclass
class PrintResult:
    """Result of a print operation."""
    success: bool
    message: str
    command_used: Optional[str] = None


ProcessResult = Result[ProcessedLabel, str]