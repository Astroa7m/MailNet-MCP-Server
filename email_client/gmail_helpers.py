import asyncio
import base64
import os.path
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from email_client.BaseEmailProvider import EmailClient
from email_client.models import EmailingStatus


class GmailClient(EmailClient):
    SCOPES = [
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/gmail.modify',
    ]

    def __init__(self, credential_file_path, token_file_path: str | None = None, token_info: dict | None = None):
        """
           Initialize GmailClient with flexible token handling.

           Args:
               credential_file_path: Path to Google OAuth2 credentials file
               token_file_path: Path to token file (for local/file-based auth)
               token_info: Token info as dict (for server-based auth where tokens are passed directly)

           Note: Provide either token_file_name OR token_info, not both.
                 If both are provided, token_info takes precedence.
           """
        super().__init__()
        self.CREDENTIAL_FILE = credential_file_path
        self.TOKEN_FILE = token_file_path
        self.token_info = token_info
        self.service = self._get_gmail_service_sync()

    def _get_gmail_service_sync(self):
        creds = None

        # priority 1, use token_info directly
        if self.token_info:
            creds = Credentials.from_authorized_user_info(self.token_info, self.SCOPES)
        # priority 2, use token_file if it exists (for local/desktop mode)
        elif self.TOKEN_FILE and os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        # refresh or create new credentials if needed
        # this will never be triggerd for remote use since invalidity will be handled by remote client
        # so without a check we are going to leave it as is
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

                # # Update token_info if it was provided originally for remote use
                # # will delete later as we don't give it back to the client
                # if self.token_info:
                #     self.token_info = json.loads(creds.to_json())

            else:
                # first time, then get new ones
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIAL_FILE, self.SCOPES
                )
                creds = flow.run_local_server(port=0, include_granted_scopes='true')

            if not self.token_info:  # save to file only if using file-based auth
                if not self.TOKEN_FILE:
                    # if token file is not provided, meaning we got new cred registration
                    # then give it a name
                    self.TOKEN_FILE = "google_token.json"
                with open(self.TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    @staticmethod
    def prep_message_raw(to, subject, body, original_msg_id=None, attachments=None):
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(body, "plain"))
            for att in attachments:
                mime_type = att.get("mime_type", "application/octet-stream")
                main_type, sub_type = (mime_type.split("/", 1) if "/" in mime_type else ("application", "octet-stream"))
                part = MIMEBase(main_type, sub_type)
                part.set_payload(base64.b64decode(att["data"]))
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{att["filename"]}"')
                message.attach(part)
        else:
            message = MIMEText(body)

        message["to"] = to
        message["subject"] = subject
        if original_msg_id:
            message["In-Reply-To"] = original_msg_id
            message["References"] = original_msg_id

        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    @staticmethod
    def extract_attachments(payload):
        attachments = []
        if 'parts' in payload:
            for part in payload['parts']:
                filename = part.get('filename')
                if filename:
                    attachments.append(filename)
        return attachments

    @staticmethod
    def extract_body(payload):
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and 'body' in part:
                    data = part['body'].get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode(errors='ignore')
        # Fallback to top-level body
        data = payload.get('body', {}).get('data')
        if data:
            return base64.urlsafe_b64decode(data).decode(errors='ignore')
        return ""

    @staticmethod
    def convert_to_datetime(timestamp):
        # noinspection PyBroadException
        try:
            return datetime.fromtimestamp(int(timestamp) / 1000).isoformat()
        except:
            return None

    def parse_msg(self, msg_data):
        payload = msg_data.get('payload', {})
        headers = payload.get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        body = self.extract_body(payload)
        attachments = self.extract_attachments(payload)
        return {
            'id': msg_data['id'],
            'threadId': msg_data.get('threadId'),
            'subject': subject,
            'sender': sender,
            'body': body,
            'attachments': attachments,
            'labelIds': msg_data.get('labelIds', []),
            'dateTime': self.convert_to_datetime(msg_data.get('internalDate'))
        }

    async def _get_labels(self):
        try:
            labels = await asyncio.to_thread(self.service.users().labels().list(userId='me').execute)
            return labels.get('labels', [])
        except Exception as e:
            print(f"Label fetch failed: {e}")
            return []

    async def send_email(self, to, subject, body, attachments=None):
        try:
            raw = self.prep_message_raw(to, subject, body, attachments=attachments)
            res = await asyncio.to_thread(
                self.service.users().messages().send(userId='me', body={'raw': raw}).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.SEND_EMAIL_SUCCESS_MESSAGE,
                      "result": res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def draft_email(self, to, subject, body, attachments=None):
        try:
            raw = self.prep_message_raw(to, subject, body, attachments=attachments)
            draft = {"message": {"raw": raw}}
            res = await asyncio.to_thread(self.service.users().drafts().create(userId='me', body=draft).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                      self.OP_MESSAGE: self.DRAFT_EMAIL_SUCCESS_MESSAGE, "result": res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def send_draft(self, draft_id):
        try:
            res = await asyncio.to_thread(
                self.service.users().drafts().send(userId='me', body={'id': draft_id}).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                      self.OP_MESSAGE: self.SEND_DRAFT_EMAIL_SUCCESS_MESSAGE, "result": res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def search_emails(self, sender=None, subject=None, has_attachment=False, after=None, before=None,
                            unread=False,
                            label=None, msg_id=None, max_results=10):
        try:
            if msg_id:
                msg_data = await asyncio.to_thread(
                    self.service.users().messages().get(userId='me', id=msg_id, format='full').execute)
                result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                          self.OP_MESSAGE: self.SEARCH_EMAIL_SUCCESS_MESSAGE, "result": self.parse_msg(msg_data)}
                return result

            query_parts = []
            if sender: query_parts.append(f"from:{sender}")
            if subject: query_parts.append(f"subject:{subject}")
            if has_attachment: query_parts.append("has:attachment")
            if after: query_parts.append(f"after:{after}")
            if before: query_parts.append(f"before:{before}")
            if unread: query_parts.append("is:unread")
            if label: query_parts.append(f"label:{label}")

            query = " ".join(query_parts)
            results = await asyncio.to_thread(
                self.service.users().messages().list(userId='me', q=query, maxResults=max_results).execute
            )
            messages = results.get('messages', [])
            enriched = []

            for msg in messages:
                msg_data = await asyncio.to_thread(
                    self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute
                )
                enriched.append(self.parse_msg(msg_data))

            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                      self.OP_MESSAGE: self.SEARCH_EMAIL_SUCCESS_MESSAGE, "result": enriched}

            return result

        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def read_emails(self, max_results=5, days_back=5):
        try:
            after = self.get_after_date(days_back)
            res = await self.search_emails(
                max_results=max_results,
                after=after
            )
            # since search returns the result in our specified format in all functions,
            # we need to unpack to avoid nesting
            messages = res['result']
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.READ_EMAIL_SUCCESS_MESSAGE,
                      "result": messages}
            return result

        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def reply_to_email(self, msg_id, body, attachments=None):
        try:
            result = (await self.search_emails(msg_id=msg_id))
            print(f"gotten result\n{result}")
            if result[self.OP_RESULT] == EmailingStatus.SUCCEEDED:
                message_info = result['result']
            else:
                raise Exception(result[self.OP_MESSAGE])

            raw = self.prep_message_raw(
                to=message_info['sender'],
                subject="Re: " + message_info['subject'],
                body=body,
                original_msg_id=msg_id,
                attachments=attachments,
            )

            message = {
                'raw': raw,
                'threadId': message_info['threadId']
            }

            res = await asyncio.to_thread(self.service.users().messages().send(userId='me', body=message).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.REPLY_TO_EMAIL_SUCCESS_MESSAGE,
                      "result": res}
            return result

        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def delete_email(self, msg_id):
        try:
            await asyncio.to_thread(self.service.users().messages().delete(userId='me', id=msg_id).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.DELETE_EMAIL_SUCCESS_MESSAGE}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def archive_email(self, msg_id):
        try:
            res = await asyncio.to_thread(
                self.service.users().messages().modify(userId='me', id=msg_id,
                                                       body={'removeLabelIds': ['INBOX']}).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                      self.OP_MESSAGE: self.ARCHIVE_EMAIL_SUCCESS_MESSAGE, "result": res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def toggle_label_email(self, msg_id, label_name, action="add"):
        try:
            labels = await self._get_labels()
            label_map = {label['name'].lower(): label['id'] for label in labels}
            label_id = label_map.get(label_name.lower())

            if not label_id:
                result = {self.OP_RESULT: EmailingStatus.FAILED,
                          self.OP_MESSAGE: f"Label '{label_name}' not found. Available labels: {','.join(sorted(label_map.keys()))}"}
                return result

            msg_data = await asyncio.to_thread(
                self.service.users().messages().get(userId='me', id=msg_id).execute
            )
            current_labels = msg_data.get('labelIds', [])

            if action == "add":
                if label_id not in current_labels:
                    res = await asyncio.to_thread(self.service.users().messages().modify(
                        userId='me',
                        id=msg_id,
                        body={'addLabelIds': [label_id]}
                    ).execute)
                    result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                              self.OP_MESSAGE: f"Added label '{label_name}' to message {msg_id}", "result": res}
                    return result
                else:
                    result = {self.OP_RESULT: EmailingStatus.FAILED,
                              self.OP_MESSAGE: f"Label '{label_name}' already present on message {msg_id}"}
                    return result

            elif action == "remove":
                if label_id in current_labels:
                    res = await asyncio.to_thread(self.service.users().messages().modify(
                        userId='me',
                        id=msg_id,
                        body={'removeLabelIds': [label_id]}
                    ).execute)
                    result = {self.OP_RESULT: EmailingStatus.SUCCEEDED,
                              self.OP_MESSAGE: f"Removed label '{label_name}' from message {msg_id}", "result": res}
                    return result
                else:
                    result = {self.OP_RESULT: EmailingStatus.FAILED,
                              self.OP_MESSAGE: f"Label '{label_name}' not present on message {msg_id}"}
                    return result

            else:
                result = {self.OP_RESULT: EmailingStatus.FAILED,
                          self.OP_MESSAGE: f"Unknown action '{action}'. Use 'add' or 'remove'."}
                return result

        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def download_attachment(self, msg_id: str, attachment_index: int = 0, save_dir: str = None):
        """
        Downloads an attachment from a specific email message.

        Args:
            msg_id: The ID of the message containing the attachment.
            attachment_index: The index of the attachment to download (0-based). Defaults to 0 (first attachment).
            save_dir: Optional directory path to save the attachment. If None, returns base64 data.

        Returns:
            dict: A dict containing operation status, message, and result with attachment data.
        """
        try:
            # Fetch the message
            msg_data = await asyncio.to_thread(
                self.service.users().messages().get(userId='me', id=msg_id, format='full').execute
            )
            payload = msg_data.get('payload', {})

            # Find all attachments with their attachment IDs
            attachments = []
            if 'parts' in payload:
                for part in payload['parts']:
                    filename = part.get('filename')
                    body = part.get('body', {})
                    attachment_id = body.get('attachmentId')
                    if filename and attachment_id:
                        attachments.append({
                            'filename': filename,
                            'attachmentId': attachment_id,
                            'mimeType': part.get('mimeType'),
                            'size': body.get('size', 0)
                        })

            if not attachments:
                result = {
                    self.OP_RESULT: EmailingStatus.FAILED,
                    self.OP_MESSAGE: f"No attachments found in message {msg_id}"
                }
                return result

            if attachment_index >= len(attachments):
                result = {
                    self.OP_RESULT: EmailingStatus.FAILED,
                    self.OP_MESSAGE: f"Attachment index {attachment_index} out of range. Message has {len(attachments)} attachment(s)."
                }
                return result

            attachment_info = attachments[attachment_index]
            attachment_id = attachment_info['attachmentId']
            filename = attachment_info['filename']

            # Fetch the actual attachment data
            attachment_data = await asyncio.to_thread(
                self.service.users().messages().attachments().get(
                    userId='me',
                    messageId=msg_id,
                    id=attachment_id
                ).execute
            )

            file_data_b64 = attachment_data.get('data', '')

            result_data = {
                'filename': filename,
                'mimeType': attachment_info['mimeType'],
                'size': attachment_info['size'],
                'total_attachments': len(attachments)
            }

            if save_dir:
                # Decode and save to file
                os.makedirs(save_dir, exist_ok=True)
                file_data = base64.urlsafe_b64decode(file_data_b64)
                filepath = os.path.join(save_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(file_data)

                result_data['filepath'] = filepath
                result_data['saved'] = True
            else:
                # Return base64 data
                result_data['data'] = file_data_b64
                result_data['saved'] = False

            result = {
                self.OP_RESULT: EmailingStatus.SUCCEEDED,
                self.OP_MESSAGE: self.DOWNLOAD_ATTACHMENT_SUCCESS_MESSAGE,
                "result": result_data
            }
            return result

        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result


def acquiring_google_token_for_personal_use():
    load_dotenv()
    google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
    GmailClient(credential_file_path=google_credentials_file)


async def test():
    load_dotenv()
    google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
    gmail_client = GmailClient(google_credentials_file)

    print("Starting tests")
    """SENDING EMAIL"""
    result = await gmail_client.send_email("test@gmail.com", "sending email from python", "Hello\nDw this is a test")
    print(f"Done sending email.\nResult: {result}")

    """DRAFTING EMAIL"""
    result = await gmail_client.draft_email("ahmed123.as27@gmail.com", "draft email from python",
                                            "Hello\nDw this is a test draft")
    print(f"Done drafting email\nResult: {result}")
    result = await gmail_client.send_draft(result['result']['id'])
    print(f"Done sending draft email.\nResult: {result}")

    """SEARCHING EMAIL"""
    result = await gmail_client.search_emails(sender="ahmed123.as27@gmail.com")
    print(f"Done searching emails, result:\n{result}\n")

    result = await gmail_client.search_emails(msg_id="180c3e86b5c1bc6a")
    print(f"Done searching emails by id, result:\n{result}\n")

    "READ EMAIL"""
    result = await gmail_client.read_emails()
    print(f"Done reading emails, result:\n{result}\n")

    """REPLYING TO EMAIL"""
    result = await gmail_client.reply_to_email(result["result"][0]["id"], "Yeah sure, cool test, wow.")
    print(f"Done replying to email.\nResult: {result}")

    """DELETING EMAIL"""
    await gmail_client.send_email("ahmed123.as27@gmail.com", "This email is going to be deleted",
                                  "Hello\nDw this will be deleted")
    to_be_deleted = await gmail_client.search_emails(subject="This email is going to be deleted", max_results=1)
    result = await gmail_client.delete_email(to_be_deleted["result"][0]["id"])
    print(f"Done deleting email.\nResult: {result}")

    """ARCHIVING EMAIL"""
    await gmail_client.send_email("ahmed123.as27@gmail.com", "This email is going to be archived",
                                  "Hello\nDw this will be archived")
    to_be_archived = await gmail_client.search_emails(subject="This email is going to be archived", max_results=1)
    result = await gmail_client.archive_email(to_be_archived["result"][0]["id"])
    print(f"Done archiving email.\nResult: {result}")

    """LABELLING EMAIL"""
    await gmail_client.send_email("ahmed123.as27@gmail.com", "This email is going to be labelled",
                                  "Hello\nDw this will be labelled")
    to_be_labelled = await gmail_client.search_emails(subject="This email is going to be labelled", max_results=1)
    result = await gmail_client.toggle_label_email(to_be_labelled["result"][0]["id"], "starred")
    print(f"Done labelling email with correct label.\nResult: {result}")

    result = await gmail_client.toggle_label_email(to_be_labelled["result"][0]["id"], "Fun")
    print(f"Done labelling email with wrong label.\nResult: {result}")

    result = await gmail_client.toggle_label_email(to_be_labelled["result"][0]["id"], "inbox")
    print(f"Done removing label from email.\nResult: {result}")


if __name__ == "__main__":
    acquiring_google_token_for_personal_use()
