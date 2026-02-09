class AutoClickerError(Exception):
    """Base exception for the application."""
    pass

class ConfigError(AutoClickerError):
    """Raised when configuration is invalid or missing."""
    pass

class OCRError(AutoClickerError):
    """Raised when OCR or Screen Capture fails."""
    pass

class ActionError(AutoClickerError):
    """Raised when an action (click/type) fails."""
    pass

class ResourceNotFoundError(AutoClickerError):
    """Raised when a required resource (file, window) is not found."""
    pass
