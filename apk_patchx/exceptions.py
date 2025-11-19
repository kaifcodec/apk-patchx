"""Custom exceptions for APKPatchx."""


class APKPatchxError(Exception):
    """Base exception for APKPatchx."""
    pass


class ToolNotFoundError(APKPatchxError):
    """Raised when a required tool is not found."""
    pass


class ValidationError(APKPatchxError):
    """Raised when input validation fails.""" 
    pass


class BuildError(APKPatchxError):
    """Raised when APK build operation fails."""
    pass


class SigningError(APKPatchxError):
    """Raised when APK signing fails."""
    pass


class ADBError(APKPatchxError):
    """Raised when ADB operation fails."""
    pass


class FridaPatchError(APKPatchxError):
    """Raised when Frida patching fails."""
    pass


class NetworkError(APKPatchxError):
    """Raised when network operation fails."""
    pass
