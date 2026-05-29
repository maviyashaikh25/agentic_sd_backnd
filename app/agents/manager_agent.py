from langchain_core.prompts import ChatPromptTemplate
from app.config import get_llm
from app.schemas.project_state import ProjectState

llm = get_llm(temperature=0.7)

def manager_agent(state: ProjectState):
    """
    Manager Agent acts as the Tech Lead. Analyzes the prompt and defines the architecture.
    """
    user_request = state.get("user_request")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert Software Architecture Manager. Your job is to analyze the user request, determine the tech stack, break down the tasks for the frontend and backend teams, and design the API contract. Provide a highly detailed plan and specify API endpoints and UI components."),
        ("user", "User Request: {user_request}")
    ])
    
    chain = prompt | llm
    
    response = chain.invoke({"user_request": user_request})
    
    print("--- Manager Agent: Plan Created ---")
    return {"plan": response.content}
