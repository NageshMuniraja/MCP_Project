from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from gmail_tools import get_unread_emails, search_emails, get_email_full

app = FastAPI()

@app.post("/tools/get_unread_emails")
def unread_emails():
    emails = get_unread_emails()
    return {
        "count": len(emails),
        "emails": emails
    }

class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 10

@app.post("/tools/search_emails")
def search_emails_endpoint(req: SearchRequest):
    results = search_emails(req.query, max_results=req.max_results)
    return {
        "count": len(results),
        "results": results
    }

class MessageRequest(BaseModel):
    message_id: str

@app.post("/tools/get_email_full")
def get_email_full_endpoint(req: MessageRequest):
    email = get_email_full(req.message_id)
    if not email:
        raise HTTPException(status_code=404, detail="Message not found")
    return email
