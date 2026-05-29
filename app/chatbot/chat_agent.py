from app.config import get_llm

llm = get_llm()

def chat_agent(message):

    result = llm.invoke(message)

    return result.content