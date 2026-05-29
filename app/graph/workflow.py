from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from langgraph.graph import END, StateGraph
import asyncio

from app.graph.state import AgentState
from app.graph.routing_logic import route_intent

# Import agents
from app.agents.manager_agent import manager_agent
from app.agents.frontend_agent import frontend_agent
from app.agents.backend_agent import backend_agent
from app.agents.qa_agent import qa_agent_backend, qa_agent_frontend
from app.agents.rag_agent import rag_node
from app.agents.debug_agent import debug_node
from app.utils.generation_output import save_generation_artifacts

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from app.api.activity_bus import publish_activity_event
import json
import re
from app.config import get_llm



ActivityPublisher = Callable[[Dict[str, Any]], Awaitable[None]]


def _agent_snapshot(active_agent: str | None, active_status: str, active_progress: int, final_state: AgentState | None = None) -> list[dict[str, Any]]:
    intent_status = "complete" if final_state and final_state.get("intent") else "idle"
    manager_status = "complete" if final_state and final_state.get("plan") else "idle"
    frontend_status = "complete" if final_state and final_state.get("frontend_code") else "idle"
    backend_status = "complete" if final_state and final_state.get("backend_code") else "idle"
    qa_status = "complete" if final_state and final_state.get("qa_feedback") else "idle"
    rag_status = "complete" if final_state and final_state.get("final_response") and final_state.get("intent") == "RAG" else "idle"
    debug_status = "complete" if final_state and final_state.get("debug_result") else "idle"
    refiner_status = "complete" if final_state and final_state.get("final_code") else "idle"

    frontend_desc = "Handles UI/UX implementation tasks"
    backend_desc = "Manages server-side logic and APIs"
    if final_state:
        if final_state.get("frontend_desc"):
            frontend_desc = final_state.get("frontend_desc")
        if final_state.get("backend_desc"):
            backend_desc = final_state.get("backend_desc")

    return [
        {
            "name": "Intent Classifier",
            "status": intent_status,
            "description": "Analyzes user intent and routes to appropriate mode",
            "progress": 100 if intent_status == "complete" else 0,
        },
        {
            "name": "Manager Agent",
            "status": "active" if active_agent == "Manager Agent" else manager_status,
            "description": "Coordinates tasks between specialized agents",
            "progress": active_progress if active_agent == "Manager Agent" else 100 if manager_status == "complete" else 0,
        },
        {
            "name": "Frontend Agent",
            "status": "active" if active_agent == "Frontend Agent" else frontend_status,
            "description": frontend_desc,
            "progress": active_progress if active_agent == "Frontend Agent" else 100 if frontend_status == "complete" else 0,
        },
        {
            "name": "Backend Agent",
            "status": "active" if active_agent == "Backend Agent" else backend_status,
            "description": backend_desc,
            "progress": active_progress if active_agent == "Backend Agent" else 100 if backend_status == "complete" else 0,
        },
        {
            "name": "QA Agent",
            "status": "active" if active_agent == "QA Agent" else qa_status,
            "description": "Performs testing and quality assurance",
            "progress": active_progress if active_agent == "QA Agent" else 100 if qa_status == "complete" else 0,
        },
        {
            "name": "Refiner Agent",
            "status": "active" if active_agent == "Refiner Agent" else refiner_status,
            "description": "Refines and compiles the final optimized code",
            "progress": active_progress if active_agent == "Refiner Agent" else 100 if refiner_status == "complete" else 0,
        },
        {
            "name": "RAG Agent",
            "status": "active" if active_agent == "RAG Agent" else rag_status,
            "description": "Retrieves contextual knowledge from database",
            "progress": active_progress if active_agent == "RAG Agent" else 100 if rag_status == "complete" else 0,
        },
        {
            "name": "Debug Agent",
            "status": "active" if active_agent == "Debug Agent" else debug_status,
            "description": "Analyzes and fixes code errors",
            "progress": active_progress if active_agent == "Debug Agent" else 100 if debug_status == "complete" else 0,
        },
    ]


def extract_detailed_descriptions(user_request: str, plan: str) -> dict:
    """
    Extracts detailed description of what frontend and backend agents are doing
    from the manager's plan and user request using the LLM.
    """
    try:
        llm = get_llm(temperature=0.1)
        prompt = (
            "You are a coordinator assistant that reads a software plan and extracts specific, action-oriented, brief tasks for Frontend and Backend agents.\n"
            "Analyze the plan and user request, then provide exactly two brief sentences of under 15 words describing what specific work they will do in this run.\n"
            "Example user request: 'make a login screen and express backend with jwt validation'\n"
            "Example plan: '[detailed architecture/steps]'\n"
            "Example output JSON:\n"
            "{\n"
            "  \"frontend_desc\": \"Building React login component, state management, and error handling views.\",\n"
            "  \"backend_desc\": \"Configuring JWT validation, /api/auth endpoints, and database schema updates.\"\n"
            "}\n\n"
            f"User Request: {user_request}\n\n"
            f"Manager Plan:\n{plan}\n\n"
            "Output ONLY the JSON object, starting with { and ending with }. Do not include markdown code blocks or any other explanation text."
        )
        response = llm.invoke(prompt)
        text = response.content.strip()
        
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n", "", text)
            text = re.sub(r"\n```$", "", text)
            text = text.strip()
            
        data = json.loads(text)
        return {
            "frontend_desc": data.get("frontend_desc", "Building React components, state management, and error handling views."),
            "backend_desc": data.get("backend_desc", "Configuring backend routes, JWT validation, and database schema updates.")
        }
    except Exception as e:
        print(f"Error extracting agent descriptions: {e}")
        return {
            "frontend_desc": "Building React components, state management, and error handling views.",
            "backend_desc": "Configuring backend routes, JWT validation, and database schema updates."
        }



async def _publish_activity(
    publisher: ActivityPublisher | None,
    *,
    phase: str,
    title: str,
    description: str,
    active_agent: str | None = None,
    active_status: str = "idle",
    active_progress: int = 0,
    timeline_label: str | None = None,
    final_state: AgentState | None = None,
) -> None:
    payload = {
        "type": "activity",
        "phase": phase,
        "title": title,
        "description": description,
        "activeAgent": active_agent,
        "activeStatus": active_status,
        "activeProgress": active_progress,
        "activeAgents": _agent_snapshot(active_agent, active_status, active_progress, final_state),
    }

    if timeline_label:
        payload["timelineEntry"] = {
            "agent": active_agent or title,
            "title": title,
            "description": description,
            "status": active_status,
            "label": timeline_label,
        }

    if publisher is not None:
        await publisher(payload)
    else:
        await publish_activity_event(payload)


async def run_workflow_with_activity(
    user_message: str,
    publisher: ActivityPublisher | None = None,
) -> Dict[str, Any]:
    state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "user_input": user_message,
        "intent": None,
        "plan": None,
        "frontend_code": None,
        "backend_code": None,
        "qa_feedback": None,
        "is_approved": None,
        "status": None,
        "action_result": None,
        "files_written": None,
        "debug_result": None,
        "final_response": None,
        "frontend_desc": None,
        "backend_desc": None,
    }

    await _publish_activity(
        publisher,
        phase="start",
        title="Intent Classifier",
        description="Classifying incoming request",
        active_agent="Intent Classifier",
        active_status="active",
        active_progress=20,
        timeline_label="2 min ago",
    )

    intent_update = intent_classifier_node(state)
    state.update(intent_update)

    await _publish_activity(
        publisher,
        phase="intent_classified",
        title="Intent Classifier",
        description=f"Classified user intent as {state.get('intent', 'UNKNOWN')} mode",
        active_agent="Intent Classifier",
        active_status="complete",
        active_progress=100,
        timeline_label="2 min ago",
        final_state=state,
    )

    intent = state.get("intent", "UNKNOWN")

    if intent == "ACTION":
        await _publish_activity(
            publisher,
            phase="manager_start",
            title="Manager Agent",
            description="Delegated tasks to agents",
            active_agent="Manager Agent",
            active_status="active",
            active_progress=55,
            timeline_label="2 min ago",
            final_state=state,
        )
        state.update(manager_node(state))
        await asyncio.sleep(2)

        # Extract detailed agent descriptions from plan
        descriptions = extract_detailed_descriptions(state.get("user_input", ""), state.get("plan", ""))
        state["frontend_desc"] = descriptions["frontend_desc"]
        state["backend_desc"] = descriptions["backend_desc"]

        await _publish_activity(
            publisher,
            phase="frontend_start",
            title="Frontend Agent",
            description=state["frontend_desc"],
            active_agent="Frontend Agent",
            active_status="active",
            active_progress=68,
            timeline_label="1 min ago",
            final_state=state,
        )
        state.update(frontend_node(state))
        await asyncio.sleep(2)

        await _publish_activity(
            publisher,
            phase="backend_start",
            title="Backend Agent",
            description=state["backend_desc"],
            active_agent="Backend Agent",
            active_status="active",
            active_progress=52,
            timeline_label="1 min ago",
            final_state=state,
        )
        state.update(backend_node(state))
        await asyncio.sleep(2)

        await _publish_activity(
            publisher,
            phase="qa_start",
            title="QA Agent",
            description="Running quality checks on the generated flow",
            active_agent="QA Agent",
            active_status="active",
            active_progress=78,
            timeline_label="just now",
            final_state=state,
        )
        state.update(qa_node(state))
        await asyncio.sleep(2)

        await _publish_activity(
            publisher,
            phase="refiner_start",
            title="Refiner Agent",
            description="Refining and optimizing into a single, efficient final code",
            active_agent="Refiner Agent",
            active_status="active",
            active_progress=60,
            timeline_label="just now",
            final_state=state,
        )
        state.update(refiner_node(state))
        await asyncio.sleep(2)

        # Save artifacts here (specifically the single final_code)
        files_written = save_generation_artifacts(
            user_request=state.get("user_input", ""),
            plan=state.get("plan", ""),
            backend_code=state.get("backend_code"),
            frontend_code=state.get("frontend_code"),
            qa_feedback=state.get("qa_feedback", ""),
            approved=state.get("is_approved", False),
            final_code=state.get("final_code"),
        )
        state["files_written"] = files_written
        
        status = "approved" if state.get("is_approved") else "needs_review"
        state["status"] = status
        action_result = "Refined code and saved as a single unified file."
        state["action_result"] = action_result
        final_output = (
            "### Action Result\n"
            f"Status: {status}\n"
            f"{action_result}\n"
            f"Files written: {len(files_written)}"
        )
        state["final_response"] = final_output
        state["messages"] = [AIMessage(content=final_output)]

        await _publish_activity(
            publisher,
            phase="complete",
            title="Refiner Agent",
            description=action_result,
            active_agent="Refiner Agent",
            active_status="complete",
            active_progress=100,
            timeline_label="just now",
            final_state=state,
        )
        return state

    if intent == "RAG":
        await _publish_activity(
            publisher,
            phase="rag_start",
            title="RAG Agent",
            description="Fetching project knowledge and references",
            active_agent="RAG Agent",
            active_status="active",
            active_progress=60,
            timeline_label="just now",
            final_state=state,
        )
        rag_update = await rag_node(state)
        state.update(rag_update)
        state["final_response"] = state["messages"][-1].content
        await _publish_activity(
            publisher,
            phase="complete",
            title="RAG Agent",
            description="Knowledge retrieval completed",
            active_agent="RAG Agent",
            active_status="complete",
            active_progress=100,
            timeline_label="just now",
            final_state=state,
        )
        return state

    await _publish_activity(
        publisher,
        phase="debug_start",
        title="Debug Agent",
        description="Analyzing failing workflow path",
        active_agent="Debug Agent",
        active_status="active",
        active_progress=60,
        timeline_label="just now",
        final_state=state,
    )
    debug_update = await debug_node(state)
    state.update(debug_update)
    state["debug_result"] = state["messages"][-1].content
    state["final_response"] = state["messages"][-1].content
    await _publish_activity(
        publisher,
        phase="complete",
        title="Debug Agent",
        description="Debug analysis completed",
        active_agent="Debug Agent",
        active_status="complete",
        active_progress=100,
        timeline_label="just now",
        final_state=state,
    )
    return state

# =========================
# INTENT NODE & ROUTER
# =========================

def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    # Extract prompt from either user_input or the latest message
    user_query = state.get("user_input", "")
    if not user_query and state.get("messages"):
        user_query = state["messages"][-1].content
    
    # We call route_intent to classify the intent
    intent = route_intent({"user_input": user_query})
    return {
        "intent": intent,
        "user_input": user_query
    }

def workflow_router(state: AgentState) -> str:
    return state["intent"]

# =========================
# ACTION MODE NODES
# =========================

def manager_node(state: AgentState) -> Dict[str, Any]:
    agent_input = {
        "user_request": state["user_input"]
    }
    result = manager_agent(agent_input)
    return {
        "plan": result.get("plan")
    }

def frontend_node(state: AgentState) -> Dict[str, Any]:
    agent_input = {
        "plan": state.get("plan"),
        "backend_code": state.get("backend_code"),
        "frontend_code": state.get("frontend_code"),
        "qa_feedback": state.get("qa_feedback"),
        "is_approved": state.get("is_approved")
    }
    result = frontend_agent(agent_input)
    return {
        "frontend_code": result.get("frontend_code")
    }

def backend_node(state: AgentState) -> Dict[str, Any]:
    agent_input = {
        "plan": state.get("plan"),
        "backend_code": state.get("backend_code"),
        "qa_feedback": state.get("qa_feedback"),
        "is_approved": state.get("is_approved")
    }
    result = backend_agent(agent_input)
    return {
        "backend_code": result.get("backend_code")
    }

def qa_node(state: AgentState) -> Dict[str, Any]:
    agent_input = {
        "plan": state.get("plan"),
        "backend_code": state.get("backend_code"),
        "frontend_code": state.get("frontend_code")
    }
    
    be_qa = qa_agent_backend(agent_input)
    fe_qa = qa_agent_frontend(agent_input)
    
    feedback = f"Backend QA: {be_qa.get('qa_feedback')}\nFrontend QA: {fe_qa.get('qa_feedback')}"
    approved = be_qa.get("is_approved", False) and fe_qa.get("is_approved", False)

    status = "approved" if approved else "needs_review"
    action_result = (
        "Frontend and backend code were generated and saved to the repository workspace."
        if approved
        else "Frontend and backend code were generated and saved to the repository workspace, but QA flagged issues for review."
    )

    return {
        "status": status,
        "action_result": action_result,
        "qa_feedback": feedback,
        "is_approved": approved,
    }

def refiner_node(state: AgentState) -> Dict[str, Any]:
    """
    Refiner Agent takes the initial code, QA feedback, and plan,
    and produces one single final, correct, and efficient code file.
    """
    user_request = state.get("user_input", "")
    plan = state.get("plan", "")
    frontend_code = state.get("frontend_code", "")
    backend_code = state.get("backend_code", "")
    qa_feedback = state.get("qa_feedback", "")
    
    print(f"\n--- Diagnostic inside refiner_node ---")
    print(f"User Request length: {len(user_request)}")
    print(f"Plan length: {len(plan) if plan else 0}")
    print(f"Frontend Code length: {len(frontend_code) if frontend_code else 0}")
    print(f"Backend Code length: {len(backend_code) if backend_code else 0}")
    print(f"QA Feedback length: {len(qa_feedback) if qa_feedback else 0}")
    
    # Prune prompt size to stay within Groq TPM limits
    pruned_plan = plan[:4000] + "\n... [TRUNCATED] ..." if plan and len(plan) > 4000 else plan
    pruned_qa = qa_feedback[:3000] + "\n... [TRUNCATED] ..." if qa_feedback and len(qa_feedback) > 3000 else qa_feedback

    llm = get_llm(temperature=0.2)
    from langchain_core.messages import SystemMessage
    messages = [
        SystemMessage(content="You are the Lead Refiner and Optimizer Agent.\n"
                              "Your job is to read the user request, plan, initial frontend and backend code, and the QA feedback.\n"
                              "You must determine the single primary code file requested (either frontend UI component or backend endpoint/server).\n"
                              "Refine, optimize, and combine that code to address all QA feedback and produce a single final, highly efficient and correct code block.\n"
                              "Start your output with a comment containing the filename (e.g. `# server.py` or `// App.jsx`) on the first line, followed by the complete code block.\n"
                              "Output ONLY the code block. Do not include markdown code block backticks (```) or other text around the code."),
        HumanMessage(content=f"User Request: {user_request}\nPlan: {pruned_plan}\n\nInitial Frontend: {frontend_code}\n\nInitial Backend: {backend_code}\n\nQA Feedback: {pruned_qa}")
    ]
    
    try:
        response = llm.invoke(messages)
        content = response.content
    except Exception as primary_err:
        print(f"Chain invoke failed: {primary_err}")
        # Try fallbacks manually to see what's happening
        print("Attempting llama-3.1-8b-instant manually...")
        try:
            fallback_llm = get_llm(model_name="llama-3.1-8b-instant", temperature=0.2)
            response = fallback_llm.invoke(messages)
            content = response.content
            print("llama-3.1-8b-instant manual fallback succeeded!")
        except Exception as f1_err:
            print(f"llama-3.1-8b-instant manual fallback failed: {f1_err}")
            print("Attempting qwen/qwen3-32b manually...")
            try:
                fallback_llm2 = get_llm(model_name="qwen/qwen3-32b", temperature=0.2)
                response = fallback_llm2.invoke(messages)
                content = response.content
                print("qwen/qwen3-32b manual fallback succeeded!")
            except Exception as f2_err:
                print(f"qwen/qwen3-32b manual fallback failed: {f2_err}")
                raise primary_err
    
    print("--- Refiner Agent: Final Code Generated ---")
    return {"final_code": content}


# =========================
# BUILD GRAPH
# =========================

def build_graph():
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("manager", manager_node)
    workflow.add_node("frontend", frontend_node)
    workflow.add_node("backend", backend_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("rag", rag_node)
    workflow.add_node("debug", debug_node)

    # Entry point
    workflow.set_entry_point("intent_classifier")

    # Conditional routing
    workflow.add_conditional_edges(
        "intent_classifier",
        workflow_router,
        {
            "ACTION": "manager",
            "RAG": "rag",
            "DEBUG": "debug"
        }
    )

    # Action flow
    workflow.add_edge("manager", "frontend")
    workflow.add_edge("frontend", "backend")
    workflow.add_edge("backend", "qa")
    workflow.add_edge("qa", END)

    # Other flows
    workflow.add_edge("rag", END)
    workflow.add_edge("debug", END)

    return workflow.compile()

graph = build_graph()