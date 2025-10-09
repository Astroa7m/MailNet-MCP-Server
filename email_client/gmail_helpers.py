import asyncio
import base64
import os.path
from datetime import datetime
from email.mime.text import MIMEText

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

    def __init__(self, credential_file, token_file):
        super().__init__()
        self.CREDENTIAL_FILE = credential_file
        self.TOKEN_FILE = token_file
        self.service = self._get_gmail_service_sync()

    def _get_gmail_service_sync(self):
        creds = None

        if os.path.exists(self.TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(self.TOKEN_FILE, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDENTIAL_FILE, self.SCOPES
                )
                creds = flow.run_local_server(port=0, include_granted_scopes='true')

            with open(self.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    @staticmethod
    def prep_message_raw(to, subject, body, original_msg_id=None):
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        if original_msg_id:
            message['In-Reply-To'] = original_msg_id
            message['References'] = original_msg_id

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return raw

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

    async def send_email(self, to, subject, body):
        try:
            raw = self.prep_message_raw(to, subject, body)
            res = await asyncio.to_thread(
                self.service.users().messages().send(userId='me', body={'raw': raw}).execute)
            result = {self.OP_RESULT: EmailingStatus.SUCCEEDED, self.OP_MESSAGE: self.SEND_EMAIL_SUCCESS_MESSAGE,
                      "result": res}
            return result
        except Exception as e:
            result = {self.OP_RESULT: EmailingStatus.FAILED, self.OP_MESSAGE: str(e)}
            return result

    async def draft_email(self, to, subject, body):
        try:
            raw = self.prep_message_raw(to, subject, body)
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

    async def reply_to_email(self, msg_id, body):
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
                original_msg_id=msg_id
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


async def test():
    credential_file = "../credentials.json"
    token_file = "../token.json"
    gmail_client = GmailClient(credential_file, token_file)

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
    asyncio.run(test())
