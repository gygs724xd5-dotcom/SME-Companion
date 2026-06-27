from __future__ import annotations


SUPPORTED_LANGUAGES = {
    "th": "Thai",
    "en": "English",
    "ar": "Arabic",
    "zh": "Chinese",
}

SUPPORTED_SURFACES = {"chat", "pdf", "invoice", "product_description"}


def build_translation_request(text: str, target_language: str, surface: str, metadata: dict | None = None) -> dict:
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError("unsupported_language")
    if surface not in SUPPORTED_SURFACES:
        raise ValueError("unsupported_surface")
    return {
        "text": text,
        "target_language": target_language,
        "surface": surface,
        "metadata": metadata or {},
        "status": "pending_translation_provider",
    }
