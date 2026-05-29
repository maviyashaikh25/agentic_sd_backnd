from dotenv import load_dotenv
import os

from langchain_groq import ChatGroq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def get_llm(model_name: str = None, temperature: float = 0.7):
    """
    Returns a configured Groq chat model.
    The model name is taken from GROQ_MODEL when available, otherwise a Groq default.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY is required to create an LLM client.")

    default_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if model_name in [None, "gpt-4", "gpt-4o", "gpt-4o-mini"]:
        model = default_model
    else:
        model = model_name

    primary = ChatGroq(
        model=model,
        temperature=temperature,
        api_key=groq_key,
    )

    if model == "llama-3.1-8b-instant":
        return primary

    fallback_1 = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=temperature,
        api_key=groq_key,
    )

    fallback_2 = ChatGroq(
        model="qwen/qwen3-32b",
        temperature=temperature,
        api_key=groq_key,
    )

    return primary.with_fallbacks([fallback_1, fallback_2])