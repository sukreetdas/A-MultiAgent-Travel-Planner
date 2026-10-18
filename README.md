# Run TripMate AI with Streamlit

This conversion keeps the existing LangGraph travel workflow and replaces the user interface with Streamlit. The FastAPI entry point (`app.py`) can remain in the repository and can still be used separately.

## Files to place in your project root

Copy these files into the same directory as your existing `backend.py`, `mcp_client.py`, and `custom_weather_mcp_server.py`:

- `streamlit_app.py` — new Streamlit frontend
- `backend.py` — updated Groq model configuration
- `mcp_client.py` — portable MCP server paths (no machine-specific Windows paths)
- `requirements.txt` — includes Streamlit and `uv`
- `custom_weather_mcp_server.py` — weather MCP server required by `mcp_client.py`
- `.env.example` — template only; never use it to store real keys
- `.gitignore` — excludes local credentials and Python environments

Keep `custom_weather_mcp_server.py` beside `mcp_client.py`.

## 1. Create your local environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The `uv` dependency provides the `uvx` command used to launch `aviationstack-mcp`.

## 2. Configure environment variables

Copy `.env.example` to `.env` and replace every placeholder with a newly generated credential. The required variables are:

- `GROQ_API_KEY`
- `TAVILY_API_KEY`
- `AVIATIONSTACK_API_KEY`
- `OPENWEATHER_API_KEY`
- `DATABASE_URL` (a reachable PostgreSQL connection URL)

`GROQ_MODEL` defaults to `openai/gpt-oss-120b`.

## 3. Start Streamlit

Run this command from the project root:

```bash
streamlit run streamlit_app.py
```

Then open `http://localhost:8501` in your browser. You can also run:

```bash
python -m streamlit run streamlit_app.py
```

## How the Streamlit interface works

The frontend calls `run_travel_agent()` directly from `backend.py`; it does not make an HTTP request to FastAPI. It shows the final plan and keeps the specialist agents' flight, hotel, weather, and itinerary outputs inside an expandable research section. A conversation thread ID is held in Streamlit session state and reused for follow-up prompts. Use **Start a new trip** to create a separate thread.

## Important runtime notes

- The backend creates a PostgreSQL checkpointer connection when imported. Therefore, `DATABASE_URL` must be configured and reachable before the first request.
- The weather MCP server is launched using the current Python interpreter and a path relative to `mcp_client.py`; keep both files in the same project directory.
- The AviationStack MCP server is launched with `uvx aviationstack-mcp`; make sure `uv` is installed in the active virtual environment and `uvx` is on `PATH`.
- The flight agent currently uses the AviationStack MCP tools to obtain airport and airline data and asks the LLM to produce route guidance. It should not be presented as a guaranteed live fare quote.
- `app.py` remains the FastAPI API entry point. It is not used when you run the Streamlit command above.

## Deploying on Streamlit Community Cloud

Push the updated source files to GitHub, choose `streamlit_app.py` as the app's main file, and put the required values in the app's **Secrets** settings using TOML key/value syntax. Do not upload `.env`. The PostgreSQL database must allow network connections from the deployment environment, and the MCP subprocess dependencies must be available in the deployed environment.

## Security

The `.env` you uploaded contained API credentials and a PostgreSQL connection string. Assume every credential in that file is compromised: rotate the Groq, Tavily, AviationStack, OpenWeather, and LangSmith keys, and change the PostgreSQL password. Keep `.env` out of Git. If it was ever committed, removing it in a later commit is not enough to invalidate the exposed credentials; rotate them anyway.
