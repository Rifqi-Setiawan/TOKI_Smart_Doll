"""Normalized provider exceptions preventing SDK-specific errors
from escaping adapters (AI-001, AI-006).
"""


class ProviderError(Exception):
    """Base exception for all external/probabilistic provider errors."""

    def __init__(self, message: str, provider_name: str = "unknown"):
        self.provider_name = provider_name
        super().__init__(f"[{provider_name}] {message}")


class ProviderTimeoutError(ProviderError):
    """Raised when an external or model call exceeds its deadline (AI-006)."""

    pass


class ProviderUnavailableError(ProviderError):
    """Raised when a provider is unreachable, down, or fails authentication (API-007)."""

    pass


class ProviderMalformedResponseError(ProviderError):
    """Raised when a provider returns an unparseable or non-conforming payload."""

    pass


class ProviderDisabledError(ProviderError):
    """Raised when an operation is requested on a disabled provider without a fallback (DEV-004)."""

    pass
