import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import aiofiles
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import ValidationError

from common import assign_doc
from common.models import Provider, EmailSettingsUpdate, EmailSettings
from email_client import BaseEmailProvider
from email_client.BaseEmailProvider import EmailClient
from email_client.gmail_helpers import GmailClient
from email_client.outlook_helpers import OutlookClient

path = Path(__file__).resolve().parents[1]
SETTINGS_PATH = path / "email_settings.json"
mcp = FastMCP("email_mcp")
_email_client: Optional[EmailClient] = None
_lock = asyncio.Lock()


async def ensure_email_client_instance() -> BaseEmailProvider:
    global _email_client
    if _email_client is None:
        async with _lock:
            # azure/outlook cred
            load_dotenv()

            azure_client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
            azure_client_secret = os.getenv("AZURE_SECRET_VALUE")
            azure_token_file_path = os.getenv("AZURE_PREFERRED_TOKEN_FILE_PATH")

            settings = await _load_email_settings()

            provider = settings.default_provider

            # google/gmail cred
            google_credentials = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
            google_token_file_path = os.getenv("GOOGLE_PREFERRED_TOKEN_FILE_PATH")
            if provider == Provider.GOOGLE:
                _email_client = GmailClient(google_credentials, google_token_file_path)
            else:
                _email_client = OutlookClient(client_id=azure_client_id, client_secret=azure_client_secret,
                                              redirect_uri="http://localhost:3000/callback",
                                              token_file=azure_token_file_path)
    return _email_client

@mcp.tool()
@assign_doc()
async def send_email(to, subject, body):
    await ensure_email_client_instance()
    return await _email_client.send_email(to, subject, body)

@mcp.tool()
@assign_doc()
async def draft_email(to: str, subject: str, body: str):
    await ensure_email_client_instance()
    return await _email_client.draft_email(to, subject, body)


@mcp.tool()
@assign_doc()
async def send_draft(draft_id: str):
    return await _email_client.send_draft(draft_id)


@mcp.tool()
@assign_doc()
async def read_emails(max_results: int = 5, days_back: int = 5):
    return await _email_client.read_emails(max_results=max_results, days_back=days_back)


@mcp.tool()
@assign_doc()
async def search_emails(
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        has_attachment: bool = False,
        after: Optional[str] = None,
        before: Optional[str] = None,
        unread: bool = False,
        label: Optional[str] = None,
        msg_id: Optional[str] = None,
        max_results: int = 10,
):
    await ensure_email_client_instance()
    return await _email_client.search_emails(
        sender, subject, has_attachment, after, before, unread, label, msg_id, max_results
    )


@mcp.tool()
@assign_doc()
async def reply_to_email(msg_id: str, body: str):
    return await _email_client.reply_to_email(msg_id, body)


@mcp.tool()
@assign_doc()
async def delete_email(msg_id: str):
    return await _email_client.delete_email(msg_id)


@mcp.tool()
@assign_doc()
async def archive_email(msg_id: str):
    return await _email_client.archive_email(msg_id)


@mcp.tool()
@assign_doc()
async def toggle_label(msg_id: str, label_name: str, action: str = "add"):
    return await _email_client.toggle_label_email(msg_id, label_name, action)


@mcp.tool()
@assign_doc()
async def download_attachment(
        msg_id: str,
        attachment_index: int = 0,
        save_dir: Optional[str] = None,
):
    """
    Downloads an attachment from a specific email message.

    Args:
        msg_id: The ID of the message containing the attachment.
        attachment_index: The index of the attachment to download (0-based). Defaults to 0 (first attachment).
        save_dir: Optional directory path to save the attachment. If None, returns base64 data.

    Returns:
        dict: A dict containing:
            - operation_status: 'succeeded' or 'failed'.
            - operation_message: Description of the download result.
            - result: Dict containing filename, filepath (if saved), mimeType, size, and optionally base64 data.
    """
    await ensure_email_client_instance()
    return await _email_client.download_attachment(msg_id, attachment_index, save_dir)


@mcp.tool()
async def load_email_settings() -> EmailSettings:
    """
    Loads the current email generation settings. These settings MUST be respected for the entire e-mailing generation.
    The LLM MUST obey to all the rules within it when crafting emails.

    Returns:
        EmailSettings: A validated configuration object containing tone,
                       style, personalization, and behavioral flags.
    """

    try:
        async with aiofiles.open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return EmailSettings(**data)
    except (FileNotFoundError, json.JSONDecodeError, ValidationError):
        return EmailSettings()


async def _load_email_settings() -> EmailSettings:
    """
    Loads the current email generation settings. These settings MUST be respected for the entire e-mailing generation.
    The LLM MUST obey to all the rules within it when crafting emails.

    Returns:
        EmailSettings: A validated configuration object containing tone,
                       style, personalization, and behavioral flags.
    """

    try:
        async with aiofiles.open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return EmailSettings(**data)
    except (FileNotFoundError, json.JSONDecodeError, ValidationError):
        return EmailSettings()


@mcp.tool()
async def update_email_settings(new_partial_settings: EmailSettingsUpdate) -> EmailSettings | tuple[str, str]:
    global _email_client
    """
    Updates the persisted email settings with partial overrides.

    This function merges incoming user preferences with the existing
    configuration, validates the result, and writes it back to disk.
    Only provided fields are overridden; all others are preserved.

    Args:
        partial_settings (EmailSettingsUpdate): A class of fields to override in the
                                 current email settings (e.g., tone, language).

    Returns:
        EmailSettings: The updated and validated configuration object. Or a Tuple dict
    """
    try:
        # get settings
        current = await _load_email_settings()
        # convert pydantic to dict
        merged = current.model_dump()
        new_partial_settings = new_partial_settings.model_dump(exclude_none=True)
        for key, value in new_partial_settings.items():
            if key in merged.keys():
                merged[key] = value
            else:
                raise ValueError(
                    f"Invalid setting '{key}'. Valid keys: {list(EmailSettings.model_fields.keys())}"
                )

        updated = EmailSettings(**merged)

        async with aiofiles.open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            await f.write(json.dumps(updated.model_dump(), indent=2, ensure_ascii=False))

        # to enforce client reinit with new provider we are going to set it to none if changed
        if current.default_provider != updated.default_provider:
            _email_client = None

        return updated

    except Exception as e:
        return "error", str(e)


if __name__ == "__main__":
    mcp.run(transport="http", host="localhost", port=911)
