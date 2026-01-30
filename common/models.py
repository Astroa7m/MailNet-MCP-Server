from enum import Enum
from typing import Literal, Optional

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
        """You are an AI email assistant for {{organization_name}}.
        "Keep messages professional, polite, and to the point."""
    )
    default_provider: Provider = Provider.GOOGLE


class EmailSettingsUpdate(BaseModel):
    language: Optional[Literal["en", "ar", "fr"]] = None
    tone: Optional[Literal["formal", "informal", "friendly", "polite", "technical"]] = None
    writing_style: Optional[Literal["clear_and_concise", "detailed", "persuasive"]] = None
    sender_name: Optional[str] = None
    organization_name: Optional[str] = None
    include_signature: Optional[bool] = None
    signature: Optional[str] = None
    preferred_greeting: Optional[str] = None
    auto_adjust_tone: Optional[bool] = None
    include_thread_context: Optional[bool] = None
    character_limit: Optional[int] = None
    prompt_prefix: Optional[str] = None
    default_provider: Optional[Literal["google", "outlook"]] = None
