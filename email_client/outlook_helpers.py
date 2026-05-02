import json
import os
import time
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv
from msal import ConfidentialClientApplication

from email_client.BaseEmailProvider import EmailClient
from email_client.models import EmailingStatus

GRAPH_API = "https://graph.microsoft.com/v1.0"


# testing at https://developer.microsoft.com/en-us/graph/graph-explorer


class GraphQueryPlanner:
    GMAIL_TO_OUTLOOK = {
        "INBOX": "Inbox",
        "SENT": "SentItems",
        "DRAFT": "Drafts",
        "SPAM": "JunkEmail",
        "TRASH": "DeletedItems",
        "ARCHIVE": "Archive",
        "IMPORTANT": "Inbox",
    }

    def __init__(self, label: Optional[str], filters: Dict[str, Any], max_results: int = 10):
        self.label = label.upper() if label else None
        self.filters = filters
        self.max_results = max_results

    def is_category_label(self) -> bool:
        return self.label and self.label not in self.GMAIL_TO_OUTLOOK or self.label in ["STARRED", "IMPORTANT"]

    def get_folder(self) -> Optional[str]:
        return self.GMAIL_TO_OUTLOOK.get(self.label, None) if self.label else None

    def to_iso8601(self, date_str: str) -> str:
        """Converts Gmail format (YYYY/MM/DD) to ISO 8601 Outlook date format"""
        dt = datetime.strptime(date_str, "%Y/%m/%d")
        return dt.strftime("%Y-%m-%dT00:00:00Z")

    def build_filter(self) -> Optional[str]:
        f = []

        # semantic flags
        if self.label == "DRAFT":
            f.append("isDraft eq true")
        if self.label == "INBOX" and self.filters.get("unread"):
            f.append("isRead eq false")
        if self.label == "ARCHIVE":
            pass  # Already scoped to Archive folder
        if self.label == "IMPORTANT":
            f.append("categories/any(c:c eq 'Important')")

        # explicit filters
        if self.filters.get("sender"):
            f.append(f"from/emailAddress/address eq '{self.filters['sender']}'")
        if self.filters.get("subject"):
            f.append(f"contains(subject,'{self.filters['subject']}')")
        if self.filters.get("has_attachment"):
            f.append("hasAttachments eq true")
        if self.filters.get("after"):
            f.append(f"receivedDateTime ge {self.to_iso8601(self.filters['after'])}")
        if self.filters.get("before"):
            f.append(f"receivedDateTime le {self.to_iso8601(self.filters['before'])}")
        if self.filters.get("unread") and self.label != "INBOX":
            f.append("isRead eq false")

        # custom category fallback
        if self.label and self.label not in self.GMAIL_TO_OUTLOOK:
            f.append(f"categories/any(c:c eq '{self.label}')")

        return " and ".join(f) if f else None

    def compose_endpoint(self) -> str:
        if self.filters.get("msg_id"):
            return f"/me/messages/{self.filters['msg_id']}"

        filter_str = self.build_filter()
        folder = self.get_folder()
        if folder:
            base = f"/me/mailFolders/{folder}/messages"
        else:
            base = f"/me/messages"

        query = []

        if filter_str:
            query.append(f"$filter={quote(filter_str, safe='()\'/ ')}")
        query.append(f"$top={self.max_results}")
        # due to the shortcoming of Graph API, adding the following param would return an error
        # though it should work perfectly fine
        # so this will stop us from getting message in a recency order
        # query.append(f"order={self.max_results}")
        endpoint = f"{base}?{'&'.join(query)}"
        return endpoint


class OutlookClient(EmailClient):
    SCOPES = [
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/MailboxSettings.ReadWrite",
        "https://graph.microsoft.com/User.Read"
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, token_file_path: str | None = None,
                 token_info: dict | None = None):
        """
            Initialize OutlookClient with flexible token handling.
            Args:
                client_id: Azure application client ID
                client_secret: Azure application client secret
                redirect_uri: OAuth redirect URI
                token_file_path: Path to token file (for local/file-based auth)
                token_info: Token info as dict (for server-based auth where tokens are passed directly)
            Note: Provide either token_file_name OR token_info, not both.
                  If both are provided, token_info takes precedence.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_file_name = token_file_path
        self.token_info = token_info
        self.authority = "https://login.microsoftonline.com/consumers"
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        self.token = self._load_or_authenticate()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _load_or_authenticate(self) -> str:
        # priority 1, use token_info directly
        if self.token_info:
            # checking if access token is still valid
            expires_at = self.token_info.get("expires_at", 0)
            if expires_at and time.time() < expires_at - 60:
                return self.token_info["access_token"]  # use access token

            # token expired, refresh it
            if self.token_info.get("refresh_token"):
                return self._refresh_token(self.token_info["refresh_token"])

            # falling back to access token even if possibly expired
            return self.token_info["access_token"]

        # priority 2, use token_file if it exists (for local/desktop mode)
        elif self.token_file_name and os.path.exists(self.token_file_name):
            with open(self.token_file_name, "r") as f:
                token_data = json.load(f)
                if token_data.get("expires_at", 0) > time.time():
                    return token_data["access_token"]
                if "refresh_token" in token_data:
                    return self._refresh_token(token_data["refresh_token"])

        if not self.token_info:
            # then we are using it locally and have no token yet
            if not self.token_file_name:
                # if token file is not provided, meaning new cred registration
                # then give it a name
                self.token_file_name = "azure_token.json"

        # launch browser for user consent
        auth_flow = self.app.initiate_auth_code_flow(
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        print(f"\n Opening browser for authentication: {auth_flow['auth_uri']}")
        webbrowser.open(auth_flow['auth_uri'])
        code = input("Paste the authorization code here: ").strip()
        auth_response = {"code": code, "state": auth_flow["state"]}
        return self._exchange_code(auth_flow, auth_response)

    def _exchange_code(self, flow: dict, auth_response: dict) -> str:
        result = self.app.acquire_token_by_auth_code_flow(flow, auth_response)
        return self._store_token(result)

    def _refresh_token(self, refresh_token: str) -> str:
        result = self.app.acquire_token_by_refresh_token(refresh_token, scopes=self.SCOPES)
        return self._store_token(result)

    def _store_token(self, result: dict) -> str:
        if "access_token" in result:
            result["expires_at"] = time.time() + result.get("expires_in", 3600)
            # only write to file in local mode
            if self.token_file_name:
                with open(self.token_file_name, "w") as f:
                    json.dump(result, f)
            return result["access_token"]
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        url = f"{GRAPH_API}{endpoint}"

        # refresh token if expired (for local mode sessions)
        if self.token_info and time.time() > self.token_info.get("expires_at", 0) - 60:
            if self.token_info.get("refresh_token"):
                self.token = self._refresh_token(self.token_info["refresh_token"])
                self.headers["Authorization"] = f"Bearer {self.token}"
                self.token_info["expires_at"] = time.time() + 3600
                self.token_info["access_token"] = self.token

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=self.headers, **kwargs) as resp:

                    if resp.status in {200, 201, 202, 204}:
                        try:
                            data = await resp.json()
                            return data
                        except aiohttp.ContentTypeError:
                            return {}

                        # If failure, try to extract error
                    try:
                        error_data = await resp.json()
                    except aiohttp.ContentTypeError:
                        error_data = {}

                    raise Exception(resp.reason, error_data.get("error"))

        except Exception as e:
            raise RuntimeError(f"Request to {endpoint} failed: {e}") from e

    @staticmethod
    def _build_attachment_list(attachments):
        if not attachments:
            return []
        return [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att["filename"],
                "contentType": att.get("mime_type", "application/octet-stream"),
                "contentBytes": att["data"],
            }
            for att in attachments
        ]

    async def send_email(self, to: str, subject: str, body: str, attachments=None) -> Dict[str, Any]:
        try:
            message = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
            att_list = self._build_attachment_list(attachments)
            if att_list:
                message["attachments"] = att_list

            send_res = await self._request("POST", "/me/sendMail", json={"message": message})
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.SEND_EMAIL_SUCCESS_MESSAGE,
                      "result": send_res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def draft_email(self, to: str, subject: str, body: str, attachments=None) -> Dict[str, Any]:
        try:
            payload = {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
                "isDraft": "true",
            }
            att_list = self._build_attachment_list(attachments)
            if att_list:
                payload["attachments"] = att_list

            draft_res = await self._request("POST", "/me/messages", json=payload)
            draft_id = {"draftId": draft_res['id']}
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.DRAFT_EMAIL_SUCCESS_MESSAGE,
                      "result": draft_id}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def send_draft(self, draft_id: str) -> Dict[str, Any]:
        try:
            send_res = await self._request("POST", f"/me/messages/{draft_id}/send")
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.SEND_DRAFT_EMAIL_SUCCESS_MESSAGE,
                      "result": send_res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def search_emails(
            self,
            sender: Optional[str] = None,
            subject: Optional[str] = None,
            has_attachment: bool = False,
            after: Optional[str] = None,
            before: Optional[str] = None,
            unread: bool = False,
            label: Optional[str] = None,
            msg_id: Optional[str] = None,
            max_results: int = 10
    ) -> Dict[str, Any]:
        planner = GraphQueryPlanner(
            label=label,
            filters={
                "sender": sender,
                "subject": subject,
                "has_attachment": has_attachment,
                "after": after,
                "before": before,
                "unread": unread,
                "msg_id": msg_id
            },
            max_results=max_results
        )
        endpoint = planner.compose_endpoint()

        try:

            search_res = await self._request("GET", endpoint)

            # if we are searching by id then we are going to get the message attr right away
            # but if we are searching with filters, then we gonna get a list of value (messages)
            messages = search_res if msg_id else search_res['value']

            def extract_important_fields(message: Dict[str, Any]) -> Dict[str, Any]:
                sender = message.get("from", {}).get("emailAddress", {})
                attachments = message.get("hasAttachments", False)
                categories = message.get("categories", [])
                body_object = message.get("body", {})
                body = message.get("bodyPreview") if body_object['contentType'] == "html" else body_object['content']
                return {
                    "id": message.get("id"),
                    "conversation_id": message.get("conversationId"),
                    "subject": message.get("subject"),
                    "sender": f"{sender.get("name")} <{sender.get("address")}>",
                    "body": body,
                    "hasAttachments": attachments,
                    "categories": categories,
                    "receivedDateTime": message.get("receivedDateTime")
                }

            if msg_id:
                result = extract_important_fields(messages)
            else:
                result = [extract_important_fields(message) for message in messages]

            result = {
                self.OP_RESULT: EmailingStatus.SUCCEEDED,
                self.OP_MESSAGE: self.SEARCH_EMAIL_SUCCESS_MESSAGE,
                "result": result
            }
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            print(result)
            return result

    async def read_emails(self, max_results: int = 5, days_back: int = 5) -> Dict[str, Any]:
        try:
            after = self.get_after_date(days_back)
            res = await self.search_emails(
                max_results=max_results,
                after=after
            )

            messages = res['result']
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.READ_EMAIL_SUCCESS_MESSAGE,
                      "result": messages}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def reply_to_email(self, msg_id: str, body: str, attachments=None) -> Dict[str, Any]:
        try:
            payload = {"comment": body}
            att_list = self._build_attachment_list(attachments)
            if att_list:
                payload["message"] = {"attachments": att_list}
            draft_resp = await self._request("POST", f"/me/messages/{msg_id}/reply", json=payload if payload else None)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.REPLY_TO_EMAIL_SUCCESS_MESSAGE,
                      "result": draft_resp}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def delete_email(self, msg_id: str) -> Dict[str, Any]:

        try:
            del_resp = await self._request("DELETE", f"/me/messages/{msg_id}")
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.DELETE_EMAIL_SUCCESS_MESSAGE,
                      "result": del_resp}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def archive_email(self, msg_id: str) -> Dict[str, Any]:
        try:
            payload = {
                "destinationId": "Archive"
            }
            archive_resp = await self._request("POST", f"/me/messages/{msg_id}/move", json=payload)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.ARCHIVE_EMAIL_SUCCESS_MESSAGE,
                      "result": archive_resp}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def toggle_label_email(
            self,
            msg_id: str,
            label_name: str,
            action: str = "add"
    ) -> Dict[str, Any]:
        endpoint = f"/me/messages/{msg_id}"
        try:
            current = await self._request("GET", endpoint)
            existing = current.get("categories", [])
        except Exception as e:
            return {
                self.OP_RESULT: EmailingStatus.FAILED,
                self.OP_MESSAGE: f"Failed to fetch message: {e}"
            }

        # normalize label
        label = label_name.strip().capitalize()

        # modify category list
        if action == "add":
            if label not in existing:
                existing.append(label)
        elif action == "remove":
            existing = [c for c in existing if c != label]
        else:
            return {
                self.OP_RESULT: EmailingStatus.FAILED,
                self.OP_MESSAGE: f"Invalid action: {action}"
            }

        # patch updated categories
        try:
            payload = {"categories": existing}
            await self._request("PATCH", endpoint, json=payload)
            return {
                self.OP_RESULT: EmailingStatus.SUCCEEDED,
                self.OP_MESSAGE: f"Label '{label}' {action}ed successfully",
                "result": {"id": msg_id, "categories": existing}
            }
        except Exception as e:
            return {
                self.OP_RESULT: EmailingStatus.FAILED,
                self.OP_MESSAGE: f"Failed to update label: {e}"
            }

    async def download_attachment(self, msg_id: str, attachment_index: int = 0, save_dir: str = None) -> Dict[str, Any]:
        """
        Downloads an attachment from a specific email message using Microsoft Graph API.

        Args:
            msg_id: The ID of the message containing the attachment.
            attachment_index: The index of the attachment to download (0-based). Defaults to 0 (first attachment).
            save_dir: Optional directory path to save the attachment. If None, returns base64 data.

        Returns:
            dict: A dict containing operation status, message, and result with attachment data.
        """
        import base64

        try:
            # List all attachments
            attachments_resp = await self._request("GET", f"/me/messages/{msg_id}/attachments")
            attachments = attachments_resp.get("value", [])

            if not attachments:
                return {
                    self.OP_RESULT: EmailingStatus.FAILED,
                    self.OP_MESSAGE: f"No attachments found in message {msg_id}"
                }

            if attachment_index >= len(attachments):
                return {
                    self.OP_RESULT: EmailingStatus.FAILED,
                    self.OP_MESSAGE: f"Attachment index {attachment_index} out of range. Message has {len(attachments)} attachment(s)."
                }

            attachment = attachments[attachment_index]
            attachment_id = attachment.get("id")
            filename = attachment.get("name", "attachment")
            content_type = attachment.get("contentType", "application/octet-stream")
            size = attachment.get("size", 0)

            # Get the attachment content
            attachment_data = await self._request("GET", f"/me/messages/{msg_id}/attachments/{attachment_id}")
            content_bytes_b64 = attachment_data.get("contentBytes", "")

            result_data = {
                'filename': filename,
                'mimeType': content_type,
                'size': size,
                'total_attachments': len(attachments)
            }

            if save_dir:
                # Decode and save to file
                os.makedirs(save_dir, exist_ok=True)
                file_data = base64.b64decode(content_bytes_b64)
                filepath = os.path.join(save_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(file_data)

                result_data['filepath'] = filepath
                result_data['saved'] = True
            else:
                # Return base64 data
                result_data['data'] = content_bytes_b64
                result_data['saved'] = False

            return {
                self.OP_RESULT: EmailingStatus.SUCCEEDED,
                self.OP_MESSAGE: self.DOWNLOAD_ATTACHMENT_SUCCESS_MESSAGE,
                "result": result_data
            }

        except Exception as e:
            return {
                self.OP_RESULT: EmailingStatus.FAILED,
                self.OP_MESSAGE: str(e)
            }


def acquiring_azure_token_for_personal_use():
    load_dotenv()
    client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
    client_secret = os.getenv("AZURE_SECRET_VALUE")
    OutlookClient(client_id=client_id, client_secret=client_secret,
                  redirect_uri="http://localhost:3000/callback")


async def test():
    load_dotenv()
    client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
    client_secret = os.getenv("AZURE_SECRET_VALUE")
    graph_client = OutlookClient(client_id=client_id, client_secret=client_secret,
                                 redirect_uri="http://localhost:3000/callback", token_file_path="graph_token.json")

    print("Starting tests")

    """SENDING EMAIL"""
    result = await graph_client.send_email("ahmed123.as27@hotmail.com", "sending email from python",
                                           "Hello\nDw this is a test")
    print(f"Done sending email.\nResult: {result}")

    """DRAFTING EMAIL"""
    result = await graph_client.draft_email("ahmed123.as27@hotmail.com", "draft email from python",
                                            "Hello\nDw this is a test draft")
    print(f"Done drafting email\n\nResult: {result}")
    result = await graph_client.send_draft(result['result']['draftId'])
    print(f"Done sending draft email.\nResult: {result}")

    """SEARCHING EMAIL"""
    result = await graph_client.search_emails(sender="ahmed123.as27@hotmail.com")
    print(f"Done searching emails, result:\n{result}\n")
    """SEARCHING EMAIL"""
    result = await graph_client.search_emails(sender="200304om@aou.edu.om", )
    print(f"Done searching emails, result:\n{result}\n")

    result = await graph_client.search_emails(msg_id=result['result'][0]['id'])
    print(f"Done searching emails by id, result:\n{result}\n")

    print("extra searching")
    result = await graph_client.search_emails(label="Starred")
    print(f"Done searching emails by category/label, result:\n{result}\n")

    result = await graph_client.search_emails(after="2025/10/5", before="2025/10/6")
    print(f"Done searching emails between dates, result:\n{result}\n")

    result = await graph_client.search_emails(label="ARCHIVE")
    print(f"Done searching emails by archive, result:\n{result}\n")

    """READ EMAIL"""
    result = await graph_client.read_emails()
    print(f"Done reading emails, result:\n{result}\n")

    """REPLYING TO EMAIL"""
    result = await graph_client.reply_to_email(result["result"][0]["id"], "Yeah sure, cool test, wow.")
    print(f"Done replying to email.\nResult: {result}")

    """DELETING EMAIL"""
    await graph_client.send_email("ahmed123.as27@hotmail.com", "This email is going to be deleted",
                                  "Hello\nDw this will be deleted")
    to_be_deleted = await graph_client.search_emails(subject="This email is going to be deleted", max_results=1)
    result = await graph_client.delete_email(to_be_deleted["result"][0]["id"])
    print(f"Done deleting email.\nResult: {result}")

    """ARCHIVING EMAIL"""
    await graph_client.send_email("ahmed123.as27@hotmail.com", "This email is going to be archived",
                                  "Hello\nDw this will be archived")
    to_be_archived = await graph_client.search_emails(subject="This email is going to be archived", max_results=1)
    result = await graph_client.archive_email(to_be_archived["result"][0]["id"])
    print(f"Done archiving email.\nResult: {result}")

    """LABELLING EMAIL"""
    await graph_client.send_email("ahmed123.as27@hotmail.com", "This email is going to be labelled",
                                  "Hello\nDw this will be labelled")
    to_be_labelled = await graph_client.search_emails(subject="This email is going to be labelled", max_results=1)
    result = await graph_client.toggle_label_email(to_be_labelled["result"][0]["id"], "starred")
    print(f"Done labelling email with correct label.\nResult: {result}")

    result = await graph_client.toggle_label_email(to_be_labelled["result"][0]["id"], "Fun")
    print(f"Done labelling email with wrong label.\nResult: {result}")

    result = await graph_client.toggle_label_email(to_be_labelled["result"][0]["id"], "inbox", action="remove")
    print(f"Done removing label from email.\nResult: {result}")


if __name__ == "__main__":
    acquiring_azure_token_for_personal_use()
