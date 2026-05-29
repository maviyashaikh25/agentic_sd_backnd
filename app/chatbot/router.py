import os
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.activity_bus import publish_activity_event
from app.graph.workflow import run_workflow_with_activity
from app.utils.db import get_db
from app.models import User, ChatSession, ChatMessage
from app.utils.auth import get_current_user

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    author: str
    content: str
    meta: Optional[str] = None
    status: Optional[str] = None
    files_written: Optional[List[str]] = []
    qa_feedback: Optional[str] = ""
    frontend_desc: Optional[str] = ""
    backend_desc: Optional[str] = ""
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    reply: str
    intent_detected: str
    status: str
    action_result: str
    files_written: List[str]
    qa_feedback: str
    frontend_desc: str
    backend_desc: str
    session_id: str

@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all chat sessions for the authenticated user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    return sessions

@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session."""
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    new_session = ChatSession(
        id=session_id,
        user_id=current_user.id,
        title="New Chat"
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session and all cascading messages."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted successfully"}

@router.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve message history for a specific session."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or access denied")
        
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = messages_result.scalars().all()
    return messages

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Verify or create session
    session = None
    if request.session_id:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == request.session_id, ChatSession.user_id == current_user.id)
        )
        session = result.scalar_one_or_none()
        
    if not session:
        # Create a new session if none provided or not found
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session = ChatSession(
            id=session_id,
            user_id=current_user.id,
            title="New Chat"
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # 2. Save user message to database
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    user_msg = ChatMessage(
        id=user_msg_id,
        session_id=session.id,
        role="user",
        author="You",
        content=request.message,
        meta="Sent to /api/chat",
        status="sent"
    )
    db.add(user_msg)
    await db.commit()

    # 3. Publish activity indicator
    await publish_activity_event({
        "type": "snapshot",
        "connectionState": "running",
    })

    # 4. Invoke the LangGraph workflow
    result = await run_workflow_with_activity(request.message)

    final_message = result.get("final_response") or result["messages"][-1].content
    intent_detected = result.get("intent", "UNKNOWN")
    status_state = result.get("status", "unknown")
    action_result = result.get("action_result", "")
    files_written = result.get("files_written", [])
    qa_feedback = result.get("qa_feedback", "")
    frontend_desc = result.get("frontend_desc", "")
    backend_desc = result.get("backend_desc", "")

    assistant_content = action_result or final_message or "Execution completed."

    # 5. Save assistant reply to database
    assistant_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    assistant_msg = ChatMessage(
        id=assistant_msg_id,
        session_id=session.id,
        role="assistant",
        author="Manager Agent",
        content=assistant_content,
        meta=f"Intent: {intent_detected}" if intent_detected else "Intent unavailable",
        status=status_state,
        files_written=files_written,
        qa_feedback=qa_feedback,
        frontend_desc=frontend_desc,
        backend_desc=backend_desc
    )
    db.add(assistant_msg)

    # 6. Auto-generate title if it's currently default
    if session.title == "New Chat":
        # First 35 chars
        title_text = request.message.strip()
        if len(title_text) > 35:
            session.title = title_text[:35] + "..."
        else:
            session.title = title_text
            
    # Mark updated time
    session.updated_at = datetime.datetime.now(datetime.timezone.utc)
    
    await db.commit()

    return {
        "reply": final_message,
        "intent_detected": intent_detected,
        "status": status_state,
        "action_result": action_result,
        "files_written": files_written,
        "qa_feedback": qa_feedback,
        "frontend_desc": frontend_desc,
        "backend_desc": backend_desc,
        "session_id": session.id
    }

@router.get("/chat/file-content")
async def get_file_content(path: str = Query(..., description="Path to the generated file")):
    # Normalizing path and validating access
    normalized_path = os.path.normpath(path)
    
    # Check if file exists
    if not os.path.exists(normalized_path):
        # Let's try relative to the backend directory or look up in projects_generated
        alt_path = os.path.join(os.getcwd(), normalized_path)
        if os.path.exists(alt_path):
            normalized_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"File not found at {normalized_path}")
            
    try:
        with open(normalized_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


