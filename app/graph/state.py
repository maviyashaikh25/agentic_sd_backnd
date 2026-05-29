from typing import TypedDict, Optional, List, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    intent: Optional[str]
    plan: Optional[str]
    frontend_code: Optional[str]
    backend_code: Optional[str]
    qa_feedback: Optional[str]
    is_approved: Optional[bool]
    status: Optional[str]
    action_result: Optional[str]
    files_written: Optional[List[str]]
    debug_result: Optional[str]
    final_response: Optional[str]
    frontend_desc: Optional[str]
    backend_desc: Optional[str]
    final_code: Optional[str]




