from enum import Enum
from typing import Literal

from pydantic import BaseModel


class Provider(str, Enum):
    GOOGLE = "google"
    OUTLOOK = "outlook"


class EmailSettings(BaseModel):
    language: Literal["en", "ar", "fr"] = "en"
    tone: Literal["formal", "informal", "friendly", "polite", "technical"] = "formal"
    writing_style: Literal["clear_and_concise", "detailed", "persuasive"] = "clear_and_concise"
    sender_name: str = "Astro"
    organization_name: str = "Kalima Tech"
    include_signature: bool = True
    signature: str = "Best regards,\n{{sender_name}}\n{{organization_name}}"
    preferred_greeting: str = "Dear {{recipient_name}},"
    auto_adjust_tone: bool = True
    include_thread_context: bool = True
    character_limit: int = 1000
    prompt_prefix: str = (
        "You are an AI email assistant for {{organization_name}}. "
        "Keep messages professional, polite, and to the point."
    )
    default_provider: Provider = Provider.GOOGLE
