import json
import os
from pathlib import Path
from typing import Optional

import aiofiles
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from pydantic import ValidationError

from common import decrypt_payload, assign_doc
from common.models import Provider, EmailSettings, EmailSettingsUpdate
from email_client import BaseEmailProvider
from email_client.gmail_helpers import GmailClient
from email_client.outlook_helpers import OutlookClient

path = Path(__file__).resolve().parents[1]
SETTINGS_PATH = path / "email_settings.json"
load_dotenv()

# if is local field is not present in env vars (no matter the value)
# then it will launch https
is_local = os.getenv("is_local", "")


async def create_email_client_instance(azure_token=None, google_token=None, redirect_uri=None) -> BaseEmailProvider:
    settings = await load_email_settings()
    provider = settings.default_provider
    # google/gmail cred
    google_credentials = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
    azure_client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
    azure_client_secret = os.getenv("AZURE_SECRET_VALUE")

    if azure_token is None and google_token is None:  # then we are running it locally
        # azure/outlook cred

        azure_token_file_path = os.getenv("AZURE_PREFERRED_TOKEN_FILE_PATH")

        google_token_file_path = os.getenv("GOOGLE_PREFERRED_TOKEN_FILE_PATH")
        if provider == Provider.GOOGLE and google_token_file_path:
            _email_client = GmailClient(credential_file_path=google_credentials,
                                        token_file_path=google_token_file_path)
        elif provider == Provider.OUTLOOK and azure_token_file_path:
            _email_client = OutlookClient(client_id=azure_client_id, client_secret=azure_client_secret,
                                          redirect_uri="http://localhost:3000/callback",
                                          token_file_path=azure_token_file_path)
        else:
            raise RuntimeError("Neither Google token file path nor Microsoft token file path is provided")
    # remotely
    else:
        if google_token:
            _email_client = GmailClient(credential_file_path=google_credentials, token_info=google_token)
        elif azure_token:
            print("Azure token from server\n", azure_token)
            _email_client = OutlookClient(client_id=azure_client_id, client_secret=azure_client_secret,
                                          redirect_uri=redirect_uri,
                                          token_info=azure_token)
        else:
            raise RuntimeError("Neither Google token nor Microsoft token is provided")

    return _email_client


def _extract_headers_if_found():
    if is_local:
        return None, None, None

    headers = get_http_headers()
    azure_token = decrypt_payload(headers['azure_token']) if 'azure_token' in headers else None
    google_token = decrypt_payload(headers['google_token']) if 'google_token' in headers else None
    redirect_uri = headers.get('redirect_uri')

    if azure_token is None and google_token is None:
        raise ValueError("No auth token provided in request headers")

    return azure_token, google_token, redirect_uri


mcp = FastMCP("email_mcp")


@mcp.tool()
@assign_doc()
async def send_email(to, subject, body):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.send_email(to, subject, body)


@mcp.tool()
@assign_doc()
async def draft_email(to: str, subject: str, body: str):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.draft_email(to, subject, body)


@mcp.tool()
@assign_doc()
async def send_draft(draft_id: str):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.send_draft(draft_id)


@mcp.tool()
@assign_doc()
async def read_emails(max_results: int = 5, days_back: int = 5):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.read_emails(max_results=max_results, days_back=days_back)


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
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.search_emails(
        sender, subject, has_attachment, after, before, unread, label, msg_id, max_results
    )


@mcp.tool()
@assign_doc()
async def reply_to_email(msg_id: str, body: str):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.reply_to_email(msg_id, body)


@mcp.tool()
@assign_doc()
async def delete_email(msg_id: str):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.delete_email(msg_id)


@mcp.tool()
@assign_doc()
async def archive_email(msg_id: str):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.archive_email(msg_id)


@mcp.tool()
@assign_doc()
async def toggle_label(msg_id: str, label_name: str, action: str = "add"):
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.toggle_label_email(msg_id, label_name, action)


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
    azure_token, google_token, redirect_uri = _extract_headers_if_found()

    email_client = await create_email_client_instance(azure_token, google_token, redirect_uri)
    return await email_client.download_attachment(msg_id, attachment_index, save_dir)


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


mcp.tool(load_email_settings)


@mcp.tool()
async def update_email_settings(new_partial_settings: EmailSettingsUpdate) -> EmailSettings | tuple[str, str]:
    """
    Updates the persisted email settings with partial overrides.

    This function merges incoming user preferences with the existing
    configuration, validates the result, and writes it back to disk.
    Only provided fields are overridden; all others are preserved.

    Args:
        new_partial_settings (EmailSettingsUpdate): A class of fields to override in the
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

        # # to enforce client reinit with new provider we are going to set it to none if changed
        # if current.default_provider != updated.default_provider:
        #     _email_client = None

        return updated

    except Exception as e:
        return "error", str(e)


if __name__ == "__main__":
    if is_local:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host="localhost", port=9111)
