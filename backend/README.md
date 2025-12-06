# Nexus Workspace Backend

Lab workspace webapp backend using SpoonOS framework with FastAPI.

## Architecture

- **FastAPI** backend with `/api/chat` endpoint
- **6 Domain Agents** using SpoonOS `ToolCallAgent` pattern:
  - ExperimentAgent
  - ProtocolAgent
  - ReagentAgent
  - RecordAgent
  - LiteratureAgent
  - ResultsAgent
- **Intent Router** for query classification and agent routing

## Setup

### 1. Create Virtual Environment

```bash
cd nexus-workspace
python3 -m venv spoon-env
source spoon-env/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
# or with uv (faster)
uv pip install -r backend/requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required variables:
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Google Gemini API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon/service key

### 4. Run Development Server

```bash
uvicorn backend.main:app --reload --port 8000
```

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── config.py            # Configuration and env loading
├── agents/              # Domain agents (ToolCallAgent)
├── tools/               # Custom tools (BaseTool)
├── services/            # Database and auth services
├── schemas/             # Pydantic models
├── middleware/          # FastAPI middleware
├── utils/               # Shared utilities
└── tests/               # Pytest test suite
```

## API Endpoints

- `POST /api/chat` - Main chat endpoint for agent interactions
- `GET /api/health` - Health check

## Testing

```bash
pytest backend/tests/
```
