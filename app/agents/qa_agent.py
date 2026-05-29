from langchain_core.prompts import ChatPromptTemplate
from app.config import get_llm
from app.schemas.project_state import ProjectState

llm = get_llm(temperature=0.0)

def qa_agent_backend(state: ProjectState):
    """QA Agent tests and reviews the backend code."""
    plan = state.get("plan", "")
    backend_code = state.get("backend_code", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert QA Engineer. Review the provided Backend code against the Manager's plan. Check for bugs, syntax errors, and missing API requirements. If the code is perfectly fine and ready, reply exactly with 'PASS'. Otherwise, describe the issues strictly."),
        ("user", "Manager's Plan: {plan}\n\nBackend Code:\n{backend_code}\n\nReview the code.")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "plan": plan, 
        "backend_code": backend_code
    })
    
    feedback = response.content
    is_approved = "PASS" in feedback.upper()
    
    print(f"--- QA Agent (Backend): {'Approved' if is_approved else 'Rejected'} ---")
    return {"qa_feedback": feedback, "is_approved": is_approved}


def qa_agent_frontend(state: ProjectState):
    """QA Agent tests and reviews the frontend code."""
    plan = state.get("plan", "")
    backend_code = state.get("backend_code", "")
    frontend_code = state.get("frontend_code", "")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert QA Engineer. Review the provided Frontend code against the Manager's plan and Backend code. Check if the API requests match the backend, check for syntax errors, and ensure styling is sufficient. If the code is perfectly fine, reply exactly with 'PASS'. Otherwise, describe the issues strictly."),
        ("user", "Manager's Plan: {plan}\n\nBackend Code:\n{backend_code}\n\nFrontend Code:\n{frontend_code}\n\nReview the frontend code.")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "plan": plan, 
        "backend_code": backend_code,
        "frontend_code": frontend_code
    })
    
    feedback = response.content
    is_approved = "PASS" in feedback.upper()
    
    print(f"--- QA Agent (Frontend): {'Approved' if is_approved else 'Rejected'} ---")
    return {"qa_feedback": feedback, "is_approved": is_approved}
