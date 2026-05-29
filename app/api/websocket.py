from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

from app.api.activity_bus import activity_bus, build_idle_activity_state
from app.graph.workflow import graph

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/activity")
async def activity_websocket(websocket: WebSocket):
    await activity_bus.connect(websocket)
    try:
        await websocket.send_json(build_idle_activity_state())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        activity_bus.disconnect(websocket)


@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 1. Receive text from the frontend
            data = await websocket.receive_text()
            
            # Send an immediate acknowledgment that the system is thinking
            await manager.send_personal_message("System: Analyzing your request...", websocket)

            # 2. Prepare the LangGraph state
            initial_state = {
                "messages": [HumanMessage(content=data)]
            }

            try:
                # 3. Invoke the graph (In a real production app, you can use .astream() 
                # here to yield intermediate steps from LangGraph back to the user)
                result = await graph.ainvoke(initial_state)
                
                # 4. Extract final message and intent
                final_message = result["messages"][-1].content
                intent = result.get("intent", "UNKNOWN")

                # You could pack this as JSON if your frontend expects it
                # For basic text streaming, we just format a string
                await manager.send_personal_message(f"[Intent: {intent}]", websocket)
                await manager.send_personal_message(f"{final_message}", websocket)
                
            except Exception as e:
                # If the LLM errors out
                await manager.send_personal_message(f"Error: Let me check my debug logs. ({str(e)})", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("A client disconnected from the chat.")
