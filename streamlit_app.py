"""Streamlit interface for TripMate AI."""

import os
import uuid
from typing import Any

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="TripMate AI | Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_runtime_secrets() -> None:
    """Load local .env values and Streamlit Cloud secrets into environment vars."""
    load_dotenv()
    secret_names = (
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "TAVILY_API_KEY",
        "AVIATIONSTACK_API_KEY",
        "OPENWEATHER_API_KEY",
        "DATABASE_URL",
        "DEFAULT_ORIGIN_IATA",
        "LANGSMITH_TRACING",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
    )
    try:
        for name in secret_names:
            if name in st.secrets and st.secrets[name] and not os.getenv(name):
                os.environ[name] = str(st.secrets[name])
    except Exception:
        # Local runs normally use .env; Streamlit secrets are optional.
        pass


load_runtime_secrets()

REQUIRED_ENV_VARS = (
    "GROQ_API_KEY",
    "TAVILY_API_KEY",
    "AVIATIONSTACK_API_KEY",
    "OPENWEATHER_API_KEY",
    "DATABASE_URL",
)


@st.cache_resource(show_spinner=False)
def get_travel_runner():
    """Import the graph once; backend.py connects to PostgreSQL at import time."""
    from backend import run_travel_agent

    return run_travel_agent


def show_agent_value(value: Any) -> None:
    if value is None or value == "":
        st.caption("No information was returned by this agent.")
    elif isinstance(value, (dict, list)):
        st.json(value)
    elif isinstance(value, str):
        st.markdown(value)
    else:
        st.write(value)


def render_assistant_message(item: dict) -> None:
    st.markdown(item.get("answer", ""))
    details = item.get("details") or {}
    if details:
        with st.expander("View specialist-agent research", expanded=False):
            with st.container():
                st.markdown("**✈️ Flight agent**")
                show_agent_value(details.get("flight_results"))
                st.divider()
                st.markdown("**🏨 Hotel research agent**")
                show_agent_value(details.get("hotel_results"))
                st.divider()
                st.markdown("**🌦️ Weather agent**")
                show_agent_value(details.get("weather_results"))
                st.divider()
                st.markdown("**🗓️ Itinerary agent**")
                show_agent_value(details.get("itinerary"))
        st.caption(f"LLM calls: {details.get('llm_calls', '—')}  ·  Thread: {details.get('thread_id', '—')}")


# Session state preserves the current conversation when Streamlit reruns.
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"tripmate_{uuid.uuid4().hex}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.title("✈️ TripMate AI")
    st.caption("Your multi-agent travel planning assistant")
    st.divider()
    st.markdown("**Your planning team**")
    st.markdown("✈️ Flight research")
    st.markdown("🏨 Hotel research")
    st.markdown("🌦️ Weather lookup")
    st.markdown("🗓️ Itinerary planning")
    st.markdown("🧠 Final trip summary")
    st.divider()
    if st.button("＋ Start a new trip", use_container_width=True):
        st.session_state.thread_id = f"tripmate_{uuid.uuid4().hex}"
        st.session_state.chat_history = []
        st.rerun()
    st.caption("Powered by LangGraph · MCP · Groq · PostgreSQL")

st.title("Plan your next journey")
st.write(
    "Describe your destination, starting point, dates, budget, and interests. "
    "TripMate coordinates its specialist agents to prepare a travel plan."
)

missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
if missing:
    st.error("Some required configuration values are missing: " + ", ".join(missing))
    st.markdown(
        "Add these variables to a local `.env` file, or configure them in "
        "Streamlit **Settings → Secrets** before submitting a trip."
    )
    st.code(
        "GROQ_API_KEY=your_groq_api_key\n"
        "TAVILY_API_KEY=your_tavily_api_key\n"
        "AVIATIONSTACK_API_KEY=your_aviationstack_api_key\n"
        "OPENWEATHER_API_KEY=your_openweather_api_key\n"
        "DATABASE_URL=postgresql://user:password@host:5432/database",
        language="bash",
    )

for entry in st.session_state.chat_history:
    with st.chat_message(entry["role"]):
        if entry["role"] == "assistant":
            render_assistant_message(entry)
        else:
            st.markdown(entry["content"])

prompt = st.chat_input(
    "Example: Plan a 5-day trip from Kolkata to Bangkok within ₹60,000",
    disabled=bool(missing),
)

if prompt:
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Coordinating flight, hotel, weather, and itinerary agents..."):
                run_travel_agent = get_travel_runner()
                result = run_travel_agent(
                    user_input=prompt,
                    thread_id=st.session_state.thread_id,
                )

            assistant_entry = {
                "role": "assistant",
                "answer": result.get("answer", "No final response was returned."),
                "details": {
                    "thread_id": result.get("thread_id"),
                    "flight_results": result.get("flight_results"),
                    "hotel_results": result.get("hotel_results"),
                    "weather_results": result.get("weather_results"),
                    "itinerary": result.get("itinerary"),
                    "llm_calls": result.get("llm_calls", 0),
                },
            }
            render_assistant_message(assistant_entry)
            st.session_state.chat_history.append(assistant_entry)
        except Exception as exc:
            error_text = str(exc)
            st.error(f"Trip planning failed: {error_text}")
            st.info(
                "Check that PostgreSQL is reachable, all API keys are valid, "
                "`uvx` is available (install the `uv` package), and the MCP "
                "servers can start. See the terminal for the full traceback."
            )
