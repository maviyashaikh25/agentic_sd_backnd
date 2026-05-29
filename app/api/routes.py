from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.chatbot.router import router as chat_router
from app.api.websocket import router as websocket_router
from app.api.projects import router as projects_router
from app.api.files import router as files_router
from app.api.memory import router as memory_router
from app.api.execution import router as execution_router

api_router = APIRouter()

# Authentication routes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Existing Chat and WebSocket routes
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(websocket_router, tags=["WebSocket"])


# New Routes
api_router.include_router(projects_router, prefix="/projects", tags=["Project Management"])
api_router.include_router(files_router, prefix="/projects/{project_id}/files", tags=["Code & Files"])
api_router.include_router(memory_router, prefix="/memory", tags=["Memory & RAG"])
api_router.include_router(execution_router, prefix="/projects/{project_id}/execute", tags=["Execution & QA"])
