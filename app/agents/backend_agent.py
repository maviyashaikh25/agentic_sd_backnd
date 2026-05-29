from langchain_core.prompts import ChatPromptTemplate
from app.config import get_llm
from app.schemas.project_state import ProjectState

llm = get_llm(temperature=0.2)

def backend_agent(state: ProjectState):
    """
    Backend Agent writes the backend code based on the Manager's plan.
    """
    plan = state.get("plan", "")
    backend_code = state.get("backend_code", "")
    qa_feedback = state.get("qa_feedback", "")
    
    system_prompt = "You are an expert Senior Backend Engineer. You write clean, scalable backend code as per tech stack requested by user."
    if qa_feedback and not state.get("is_approved"):
         system_prompt += " The QA team rejected your code. Address the following QA feedback to fix it."

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Manager's Plan: {plan}\n\nCurrent Code (if any): {backend_code}\n\nQA Feedback (if any): {qa_feedback}\n\nGenerate or update the backend code. Output ONLY the code.")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({
        "plan": plan, 
        "backend_code": backend_code, 
        "qa_feedback": qa_feedback
    })
    
    print("--- Backend Agent: Code Generated ---")
    return {"backend_code": response.content}
