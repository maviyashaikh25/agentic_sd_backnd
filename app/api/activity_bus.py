from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class ActivityBus:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }

        for websocket in list(self.connections):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)


activity_bus = ActivityBus()


def build_idle_activity_state() -> dict[str, Any]:
    return {
        "type": "snapshot",
        "connectionState": "idle",
        "activeAgents": [
            {
                "name": "Intent Classifier",
                "status": "complete",
                "description": "Analyzes user intent and routes to appropriate mode",
                "progress": 100,
            },
            {
                "name": "Manager Agent",
                "status": "active",
                "description": "Coordinates tasks between specialized agents",
                "progress": 66,
            },
            {
                "name": "Frontend Agent",
                "status": "active",
                "description": "Handles UI/UX implementation tasks",
                "progress": 68,
            },
            {
                "name": "Backend Agent",
                "status": "idle",
                "description": "Manages server-side logic and APIs",
                "progress": 0,
            },
            {
                "name": "QA Agent",
                "status": "idle",
                "description": "Performs testing and quality assurance",
                "progress": 0,
            },
            {
                "name": "RAG Agent",
                "status": "idle",
                "description": "Retrieves contextual knowledge from database",
                "progress": 0,
            },
            {
                "name": "Debug Agent",
                "status": "idle",
                "description": "Analyzes and fixes code errors",
                "progress": 0,
            },
        ],
    }


async def publish_activity_event(payload: dict[str, Any]) -> None:
    await activity_bus.broadcast(payload)