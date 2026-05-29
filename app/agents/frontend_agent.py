from langchain_core.prompts import ChatPromptTemplate
from app.config import get_llm
from app.schemas.project_state import ProjectState

llm = get_llm(temperature=0.2)

def frontend_agent(state: ProjectState):
    """
    Frontend Agent writes the frontend code based on the Manager's plan.
    """
    plan = state.get("plan", "")
    backend_code = state.get("backend_code", "")
    frontend_code = state.get("frontend_code", "")
    qa_feedback = state.get("qa_feedback", "")
    
    system_prompt = "You are an expert Senior Frontend Engineer. You write modern, responsive frontend code, typically using React or Vue, and integrate perfectly with the provided backend APIs."
    
    if qa_feedback and not state.get("is_approved"):
         system_prompt += " The QA team rejected your frontend code. Address the following QA feedback to fix it."

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Manager's Plan: {plan}\n\nBackend Code: {backend_code}\n\nCurrent Frontend Code (if any): {frontend_code}\n\nQA Feedback (if any): {qa_feedback}\n\nGenerate or update the frontend code based on the backend code and the plan. Output ONLY the code.")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "plan": plan, 
        "backend_code": backend_code, 
        "frontend_code": frontend_code, 
        "qa_feedback": qa_feedback
    })
    
    print("--- Frontend Agent: Code Generated ---")
    return {"frontend_code": response.content}
