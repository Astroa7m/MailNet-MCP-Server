import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import ValidationError

from common import assign_doc
from common.models import EmailSettings, Provider, EmailSettingsUpdate
from email_client import BaseEmailProvider
from email_client.gmail_helpers import GmailClient
from email_client.outlook_helpers import OutlookClient

app = FastAPI(title="Email MCP Server")

path = Path(__file__).resolve().parents[1]

SETTINGS_PATH = path / "email_settings.json"

#todo: Make settings injection more neatly
#todo: Settings should be retrieved again after manual refreshing or via update_email_settings func

async def get_client() -> BaseEmailProvider:
    # azure/outlook cred
    load_dotenv()

    azure_client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
    azure_client_secret = os.getenv("AZURE_SECRET_VALUE")
    azure_token_file_path = os.getenv("AZURE_PREFERRED_TOKEN_FILE_PATH")

    settings = await load_email_settings()

    provider = settings.default_provider

    # google/gmail cred
    google_credentials = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
    google_token_file_path = os.getenv("GOOGLE_PREFERRED_TOKEN_FILE_PATH")
    if provider == Provider.GOOGLE:
        client = GmailClient(google_credentials, google_token_file_path)
    else:
        client = OutlookClient(client_id=azure_client_id, client_secret=azure_client_secret,
                               redirect_uri="http://localhost:3000/callback", token_file=azure_token_file_path)
    return client


@app.post("/send_email")
@assign_doc()
async def send_email(to, subject, body, client=Depends(get_client)):
    return await client.send_email(to, subject, body)


@app.post("/draft_email")
@assign_doc()
async def draft_email(to: str, subject: str, body: str, client=Depends(get_client)):
    return await client.draft_email(to, subject, body)


@app.post("/send_draft")
@assign_doc()
async def send_draft(draft_id: str, client=Depends(get_client)):
    return await client.send_draft(draft_id)


@app.get("/read_emails")
@assign_doc()
async def read_emails(max_results: int = 5, days_back: int = 5, client=Depends(get_client)):
    return await client.read_emails(max_results=max_results, days_back=days_back)


@app.get("/search_emails")
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
        client=Depends(get_client)
):
    return await client.search_emails(
        sender, subject, has_attachment, after, before, unread, label, msg_id, max_results
    )


@app.post("/reply_to_email")
@assign_doc()
async def reply_to_email(msg_id: str, body: str, client=Depends(get_client)):
    return await client.reply_to_email(msg_id, body)


@app.delete("/delete_email/{msg_id}")
@assign_doc()
async def delete_email(msg_id: str, client=Depends(get_client)):
    return await client.delete_email(msg_id)


@app.post("/archive_email/{msg_id}")
@assign_doc()
async def archive_email(msg_id: str, client=Depends(get_client)):
    return await client.archive_email(msg_id)


@app.post("/toggle_label")
@assign_doc()
async def toggle_label(msg_id: str, label_name: str, action: str = "add", client=Depends(get_client)):
    return await client.toggle_label_email(msg_id, label_name, action)


@app.get("/load_email_settings")
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


@app.post("/update_email_settings")
async def update_email_settings(new_partial_settings: EmailSettingsUpdate) -> EmailSettingsUpdate | Tuple[str, str]:
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
        current = await load_email_settings()
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

        return updated

    except Exception as e:
        return "error", str(e)
