"""
Clinivue backend -- minimal version matching the frontend's chat contract.

The frontend (frontend/app/pages/index.vue) expects:
  POST {chatEndpoint}
    multipart/form-data: conversationId, text, images[]
    -> { "message": { "text": "..." } }

  GET {chatEndpoint}/history?conversationId=...
    -> ChatMessage[]   (see frontend/app/types/chat.ts)

This version stores conversations in memory (resets on restart) and returns
a placeholder assistant reply instead of running the real vision/RAG
pipeline described in docs/ideas.md. Swap `generate_reply()` for a real
model call when that's ready -- everything else (contract, image handling,
history) is already wired to match the frontend.

Run with:
    uvicorn main:app --reload

Then in frontend/app/pages/index.vue, set:
    const chatEndpoint = 'http://127.0.0.1:8000/chat'
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Clinivue Backend")

# Nuxt dev server runs on :3000 by default -- adjust if yours differs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves saved images back to the frontend so ImageUrls in chat history
# resolve to something real instead of a broken link.
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ---------------------------------------------------------------------------
# Matches frontend/app/types/chat.ts::ChatMessage
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    id: str
    sender: Literal["user", "assistant"]
    text: str
    imageUrls: Optional[list[str]] = None
    createdAt: str
    loading: Optional[bool] = None
    error: Optional[bool] = None


# In-memory conversation store: conversationId -> list of ChatMessage.
# Fine for a hackathon demo; swap for Postgres/Supabase if you need
# messages to survive a backend restart.
conversations: dict[str, list[ChatMessage]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_reply(text: str, image_count: int) -> str:
    """Placeholder for the real vision/RAG pipeline in docs/ideas.md.
    Swap this out for the actual model call once it exists."""
    if image_count:
        return (
            f"Received {image_count} image(s) and your message: \"{text}\". "
            "This is a placeholder response -- the real triage/retrieval "
            "pipeline isn't wired in yet."
        )
    return f"Placeholder response to: \"{text}\""


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/chat")
async def post_chat_message(
    conversationId: str = Form(...),
    text: str = Form(""),
    images: list[UploadFile] = File(default=[]),
):
    saved_image_urls: list[str] = []
    for image in images:
        ext = Path(image.filename or "upload").suffix or ".jpg"
        saved_name = f"{uuid.uuid4().hex}{ext}"
        saved_path = UPLOAD_DIR / saved_name
        contents = await image.read()
        saved_path.write_bytes(contents)
        saved_image_urls.append(f"/uploads/{saved_name}")

    conversations.setdefault(conversationId, [])

    user_message = ChatMessage(
        id=uuid.uuid4().hex,
        sender="user",
        text=text,
        imageUrls=saved_image_urls or None,
        createdAt=now_iso(),
    )
    conversations[conversationId].append(user_message)

    reply_text = generate_reply(text, len(saved_image_urls))
    assistant_message = ChatMessage(
        id=uuid.uuid4().hex,
        sender="assistant",
        text=reply_text,
        createdAt=now_iso(),
    )
    conversations[conversationId].append(assistant_message)

    # Shape matches what index.vue expects: response.message.text
    return {"message": {"text": reply_text}}


@app.get("/chat/history", response_model=list[ChatMessage])
def get_chat_history(conversationId: str):
    return conversations.get(conversationId, [])