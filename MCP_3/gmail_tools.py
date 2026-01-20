from gmail_auth import get_gmail_service
import base64
from typing import List, Dict, Any


def _get_headers_map(headers: List[Dict[str, str]]) -> Dict[str, str]:
    return {h.get("name"): h.get("value") for h in headers}


def _extract_text_from_payload(payload: Dict[str, Any]) -> str:
    """Recursively extract the text/plain content from a message payload."""
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    parts = payload.get("parts", [])

    # If this payload is text/plain and has data, decode it.
    if mime_type == "text/plain" and body.get("data"):
        data = body.get("data")
        try:
            decoded = base64.urlsafe_b64decode(data + '==').decode("utf-8", errors="replace")
            return decoded
        except Exception:
            return ""

    # If multipart, walk children and concatenate text/plain parts.
    texts = []
    for part in parts:
        part_text = _extract_text_from_payload(part)
        if part_text:
            texts.append(part_text)

    return "\n".join(texts)


def list_unread_emails(max_results: int = 5) -> List[Dict[str, Any]]:
    """Return a short summary list of unread emails. Each entry contains id, threadId, headers (From, To, Subject, Date) and a short snippet.

    This is suitable for quickly answering questions like "Do I have any unread emails?" or "What is the new email I got?".
    """
    service = get_gmail_service()

    result = service.users().messages().list(
        userId="me",
        labelIds=["UNREAD"],
        maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    summaries = []

    for msg in messages:
        data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()

        headers = _get_headers_map(data.get("payload", {}).get("headers", []))
        snippet = data.get("snippet", "")
        summaries.append({
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "headers": headers,
            "snippet": snippet
        })

    return summaries


def get_email_full(message_id: str) -> Dict[str, Any]:
    """Return the full email content for a specific message id.

    The returned dict includes:
    - id, threadId
    - headers (map)
    - body (text extracted from text/plain parts)
    - attachments (list of {filename, mimeType, attachmentId, size, content_preview})

    Attachments content is fetched for text-like attachments and a short preview is included to keep payloads small.
    """
    service = get_gmail_service()
    data = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    headers = _get_headers_map(data.get("payload", {}).get("headers", []))
    body = _extract_text_from_payload(data.get("payload", {}))

    attachments = []
    # Walk parts to find attachments
    def _walk_parts(parts):
        for p in parts or []:
            filename = p.get("filename")
            body = p.get("body", {})
            part_id = p.get("partId")
            mime_type = p.get("mimeType")

            if filename and body and (body.get("attachmentId") or body.get("data")):
                attachment_info = {
                    "filename": filename,
                    "mimeType": mime_type,
                    "attachmentId": body.get("attachmentId"),
                    "size": body.get("size")
                }
                # Try to fetch small text attachments content preview
                if body.get("attachmentId"):
                    try:
                        att = service.users().messages().attachments().get(
                            userId="me",
                            messageId=message_id,
                            id=body.get("attachmentId")
                        ).execute()
                        att_data = att.get("data")
                        if att_data:
                            decoded = base64.urlsafe_b64decode(att_data + '==').decode("utf-8", errors="replace")
                            # Keep a short preview
                            attachment_info["content_preview"] = decoded[:1000]
                        else:
                            attachment_info["content_preview"] = None
                    except Exception:
                        attachment_info["content_preview"] = None

                attachments.append(attachment_info)

            # Recurse into nested parts
            child_parts = p.get("parts")
            if child_parts:
                _walk_parts(child_parts)

    _walk_parts(data.get("payload", {}).get("parts", []))

    return {
        "id": data.get("id"),
        "threadId": data.get("threadId"),
        "headers": headers,
        "body": body,
        "attachments": attachments,
        "snippet": data.get("snippet")
    }


def search_emails(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search the user's mailbox using Gmail query language and return short summaries of matching messages."""
    service = get_gmail_service()
    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    results = []
    for msg in messages:
        data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        headers = _get_headers_map(data.get("payload", {}).get("headers", []))
        results.append({
            "id": msg["id"],
            "threadId": msg.get("threadId"),
            "headers": headers,
            "snippet": data.get("snippet")
        })

    return results


def build_context_for_llm(email: Dict[str, Any], include_attachments: bool = True, attachment_preview_chars: int = 500) -> str:
    """Build a plain-text context string for the LLM from an email dict produced by get_email_full or list/search results.

    The returned string is intentionally concise so the client can pass it as the LLM prompt context when answering user questions about Gmail (e.g., "any mail from Google?", "open the latest mail and summarize", "read attachment and summarize").
    """
    headers = email.get("headers", {})
    subject = headers.get("Subject", "(no subject)")
    sender = headers.get("From", "(unknown sender)")
    date = headers.get("Date", "(unknown date)")
    snippet = email.get("snippet", "")
    body = email.get("body") or snippet or ""

    ctx = [f"Subject: {subject}", f"From: {sender}", f"Date: {date}", "", "Body:", body[:2000]]

    if include_attachments:
        atts = email.get("attachments", [])
        if atts:
            ctx.append("\nAttachments:")
            for a in atts:
                preview = a.get("content_preview")
                if preview:
                    ctx.append(f"- {a.get('filename')} ({a.get('mimeType')}): {preview[:attachment_preview_chars]}")
                else:
                    ctx.append(f"- {a.get('filename')} ({a.get('mimeType')}): (no text preview available)")

    return "\n".join(ctx)


# Backwards-compatible alias used by existing code
def get_unread_emails(max_results=5):
    return list_unread_emails(max_results=max_results)
