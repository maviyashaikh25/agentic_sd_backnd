from langchain_core.tools import create_retriever_tool
from app.rag.vector_store import get_vector_store

def get_rag_tool():
    # Assumes vector_store.py has a function returning Chroma retriever
    retriever = get_vector_store().as_retriever(search_kwargs={"k": 5})
    
    rag_tool = create_retriever_tool(
        retriever=retriever,
        name="project_knowledge_retriever",
        description="Search for project specs, current architecture, existing files, or API endpoints. Input should be a search query."
    )
    return rag_tool
