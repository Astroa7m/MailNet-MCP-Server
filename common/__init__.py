DOCSTRINGS = {
    "send_email": """
        Sends an email to the specified recipient.

        Used to initiate outbound communication. Returns metadata about the sent message.

        Args:
            to (str): Recipient email address.
            subject (str): Subject line of the email.
            body (str): Content of the email body (plain text or HTML).

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed' (EmailingStatus enum).
                - operation_message: Description of the operation result.
                - result: Dict containing metadata (e.g., message ID, thread ID).""",
    "draft_email": """
     Creates a draft email without sending it.

        Used to prepare messages for later review or scheduling.

        Args:
            to (str): Intended recipient email address.
            subject (str): Subject line of the draft.
            body (str): Content of the draft message.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the draft creation result.
                - result: Dict containing metadata (e.g., draft ID).""",
    "send_draft": """
            Sends a previously created draft email.

        Args:
            draft_id (str): Unique identifier of the draft message.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the send operation.
                - result: Dict containing metadata about the sent message.""",
    "search_emails": """
        Searches for emails matching the given filters.

        Used to locate specific messages or threads. Returns a list unless `msg_id` is provided.

        Args:
            sender (Optional[str]): Filter by sender email address.
            subject (Optional[str]): Filter by subject line.
            has_attachment (bool): Whether to filter for messages with attachments.
            after (Optional[str]): Start date in 'YYYY/MM/DD' format.
            before (Optional[str]): End date in 'YYYY/MM/DD' format.
            unread (bool): Whether to filter for unread messages.
            label (Optional[str]): Filter by label or category, can also search for sent emails with "SENT" label.
            msg_id (Optional[str]): Search for a specific message ID.
            max_results (int): Maximum number of results to return.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the search outcome.
                - result: List of message metadata dicts (or single dict if `msg_id` is used).""",
    "read_emails": """
        Reads recent emails received within the past `days_back` days.

        Used to retrieve inbox context for summarization, triage, or reply.

        Args:
            max_results (int): Maximum number of messages to return.
            days_back (int): Number of days to look back from today.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the read operation.
                - result: List of message metadata dicts, sorted by recency.""",
    "reply_to_email": """        Sends a reply to the specified message.

        Used to continue a conversation thread.

        Args:
            msg_id (str): ID of the message to reply to.
            body (str): Content of the reply message.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the reply operation.
                - result: Dict containing metadata about the reply message.""",
    "delete_email": """
        Deletes the specified message.

        Args:
            msg_id (str): ID of the message to delete.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the deletion result.
                - result: Dict containing deletion metadata or confirmation.""",
    "archive_email": """
        Archives the specified message (e.g., removes it from the inbox).

        Args:
            msg_id (str): ID of the message to archive.

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the archive result.
                - result: Dict containing updated message metadata.""",
    "toggle_label_email": """
        Adds or removes a label/category from the specified message.

        Used to organize or tag messages

        Args:
            msg_id (str): ID of the message to modify.
            label_name (str): Name of the label or category.
            action (str): Either "add" or "remove".

        Returns:
            dict[str, Any]: A dict containing:
                - operation_status: 'succeeded' or 'failed'.
                - operation_message: Description of the label toggle result.
                - result: Dict containing updated message metadata.""",
}


def assign_doc(name=None):
    def decorator(func):
        key = name or func.__name__
        func.__doc__ = DOCSTRINGS.get(key, "")
        return func

    return decorator
