from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, func
from app.utils.db import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tech_stack = Column(JSON, nullable=False, default=list)
    status = Column(String(50), nullable=False, default="initialized")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(50), primary_key=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="uploaded")
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(50), primary_key=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    author = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    meta = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    files_written = Column(JSON, nullable=True)
    qa_feedback = Column(Text, nullable=True)
    frontend_desc = Column(Text, nullable=True)
    backend_desc = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

