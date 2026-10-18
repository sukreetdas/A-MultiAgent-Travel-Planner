"""MCP connections for TripMate AI.

The weather MCP server path is resolved relative to this file so the project
works outside the original developer's Windows machine.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Add it to your .env file or Streamlit secrets.")

# Resolve the custom server from the project directory, not a machine-specific path.
WEATHER_SERVER_PATH = Path(__file__).resolve().with_name("custom_weather_mcp_server.py")
if not WEATHER_SERVER_PATH.is_file():
    raise FileNotFoundError(
        f"Weather MCP server was not found at: {WEATHER_SERVER_PATH}. "
        "Keep custom_weather_mcp_server.py beside mcp_client.py."
    )

# uvx is installed by the `uv` dependency added to requirements.txt.
UVX_COMMAND = shutil.which("uvx") or "uvx"

llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY)

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
        },
        "aviationstack": {
            "transport": "stdio",
            "command": UVX_COMMAND,
            "args": ["aviationstack-mcp"],
            "env": {"AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY or ""},
        },
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(WEATHER_SERVER_PATH)],
            "env": {"OPENWEATHER_API_KEY": OPENWEATHER_API_KEY or ""},
        },
    }
)


async def get_all_tools():
    tools = await client.get_tools()
    print("\nAvailable MCP Tools:\n")
    for tool in tools:
        print(tool.name)


search_tool = None
aviation_tools = {}


async def initialize_mcp():
    global search_tool, aviation_tools

    if search_tool is not None and aviation_tools:
        return

    tools = await client.get_tools()
    print("\nAvailable MCP Tools:\n")
    for tool in tools:
        print(tool.name)

    search_tool = next(tool for tool in tools if tool.name == "tavily_search")
    aviation_tools = {tool.name: tool for tool in tools if tool.name != "tavily_search"}


async def tavily_mcp_search(query: str):
    await initialize_mcp()
    return await search_tool.ainvoke({"query": query})


async def aviation_mcp_call(tool_name: str, tool_args: dict | None = None):
    tools = await client.get_tools()
    tool = next((item for item in tools if item.name == tool_name), None)
    if tool is None:
        available = ", ".join(item.name for item in tools)
        raise RuntimeError(f"MCP tool '{tool_name}' was not found. Available tools: {available}")
    return await tool.ainvoke(tool_args or {})


weather_tool = None
forecast_tool = None


async def initialize_weather_tools():
    global weather_tool, forecast_tool

    if weather_tool is not None and forecast_tool is not None:
        return

    tools = await client.get_tools()
    weather_tool = next(tool for tool in tools if tool.name == "get_current_weather")
    forecast_tool = next(tool for tool in tools if tool.name == "get_forecast")


async def weather_mcp_search(city: str):
    await initialize_weather_tools()
    return await weather_tool.ainvoke({"city": city})


async def forecast_mcp_search(city: str):
    await initialize_weather_tools()
    return await forecast_tool.ainvoke({"city": city})


def extract_destination(query: str):
    prompt = f"""
    Extract only the destination city or country.

    Query:
    {query}

    Return only destination name.
    """
    response = llm.invoke(prompt)
    return response.content.strip()
