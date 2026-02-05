"""
DuggerBootTools Exception Classes

Custom exceptions for better error handling and user feedback.
"""


class DuggerBootError(Exception):
    """Base exception for DuggerBootTools operations."""
    
    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


class TemplateNotFoundError(DuggerBootError):
    """Raised when a requested template doesn't exist."""
    pass


class ValidationError(DuggerBootError):
    """Raised when project validation fails."""
    pass


class GitError(DuggerBootError):
    """Raised when Git operations fail."""
    pass


class DependencyError(DuggerBootError):
    """Raised when DuggerLinkTools dependency is not found."""
    pass