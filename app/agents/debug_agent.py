from app.config import get_llm


async def debug_node(state):
    llm = get_llm(temperature=0)
    result = await llm.ainvoke(state["messages"])
    return {"messages": [result]}
