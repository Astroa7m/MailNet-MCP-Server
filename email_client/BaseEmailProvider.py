from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Tuple, Dict, Union, List, Optional, Any
from mcp_server.common import assign_doc


class EmailClient(ABC):
    """
     Abstract base class for email client integrations.

    This interface defines a unified set of asynchronous methods for interacting with email providers
    such as Gmail, Outlook, or custom IMAP services. It enables agentic orchestration of email workflows
    including sending, reading, searching, replying, archiving, and label management.

    Concrete implementations (e.g., GmailClient, OutlookClient (WIP)) must implement all methods to ensure
    consistent behavior across providers.

    All methods within this class return a tuple of the following keys:
    - 'operation_status': Indicates operation success/failure status. Possible values: 'succeeded' or 'failed'.
    Based on Enum class (EmailingStatus) under util module

    - 'operation_message': A descriptive message about the current operation success/failure.

    - 'result': Could contain either:
        * A dict contains metadata about the email being processed (e.g., message ID, thread ID).
        * A list of dict containing metadata, which could happen in two scenarios only.
        By either calling read_emails which returns a list or calling search_emails without msg_id
    """
    SCOPES: List[str]
    OP_RESULT = "operation_status"
    OP_MESSAGE = "operation_message"
    SEND_EMAIL_SUCCESS_MESSAGE = "Email has been sent successfully"
    DRAFT_EMAIL_SUCCESS_MESSAGE = "Email draft has been created successfully"
    SEND_DRAFT_EMAIL_SUCCESS_MESSAGE = "Email draft has been sent successfully"
    SEARCH_EMAIL_SUCCESS_MESSAGE = "Email has been searched successfully"
    READ_EMAIL_SUCCESS_MESSAGE = "Emails have been read successfully"
    REPLY_TO_EMAIL_SUCCESS_MESSAGE = "Replied to email successfully"
    DELETE_EMAIL_SUCCESS_MESSAGE = "Email has been deleted successfully"
    ARCHIVE_EMAIL_SUCCESS_MESSAGE = "Emails have been archived successfully"

    @assign_doc()
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def draft_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def send_draft(self, draft_id: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
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
        pass

    @assign_doc()
    @abstractmethod
    async def read_emails(self, max_results: int = 5, days_back: int = 5) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def reply_to_email(self, msg_id: str, body: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def delete_email(self, msg_id: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def archive_email(self, msg_id: str) -> Dict[str, Any]:
        pass

    @assign_doc()
    @abstractmethod
    async def toggle_label_email(self, msg_id: str, label_name: str, action: str = "add") -> Dict[str, Any]:
        pass

    @staticmethod
    def get_after_date(days_back=5):
        cutoff = datetime.now() - timedelta(days=days_back)
        return cutoff.strftime('%Y/%m/%d')