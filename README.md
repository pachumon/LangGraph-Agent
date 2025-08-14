# LangGraph Gemini Agent API

A session-based conversational AI API built with FastAPI, LangGraph, and Google's Gemini model. This API provides persistent conversation sessions where users can have multi-turn conversations with the AI agent.

## Features

- **Session-based Conversations**: Maintain context across multiple queries
- **LangGraph Integration**: Sophisticated workflow management with state persistence
- **Google Gemini AI**: Powered by Gemini 2.0 Flash model
- **RESTful API**: Clean, documented endpoints
- **Automatic Session Management**: Session timeout and cleanup
- **Production Ready**: Proper error handling, logging, and validation

## Project Structure

```
app/
├── core/           # Configuration and settings
├── models/         # Pydantic schemas
├── services/       # Business logic services
└── api/
    └── v1/         # API endpoints
        ├── sessions.py   # Session management
        ├── chat.py      # Chat functionality
        └── health.py    # Health checks
```

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Run the API

```bash
# Using the runner script
python run_api.py

# Or directly with uvicorn
uvicorn app.main:app --reload
```

The API will be available at:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## API Usage

### 1. Create a Session

```bash
curl -X POST "http://localhost:8000/api/v1/sessions/" \
     -H "Content-Type: application/json" \
     -d "{}"
```

Response:
```json
{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "created_at": 1703123456.789,
    "message_count": 0
}
```

### 2. Send a Query

```bash
curl -X POST "http://localhost:8000/api/v1/chat/{session_id}/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the meaning of life?"}'
```

### 3. Get Conversation History

```bash
curl "http://localhost:8000/api/v1/chat/{session_id}/history"
```

### 4. End Session

```bash
curl -X DELETE "http://localhost:8000/api/v1/sessions/{session_id}"
```

## API Endpoints

### Sessions
- `POST /api/v1/sessions/` - Create new session
- `GET /api/v1/sessions/{session_id}` - Get session info
- `DELETE /api/v1/sessions/{session_id}` - End session

### Chat
- `POST /api/v1/chat/{session_id}/query` - Send query to AI
- `GET /api/v1/chat/{session_id}/history` - Get conversation history

### Health
- `GET /api/v1/health` - Health check
- `GET /api/v1/stats` - System statistics

## Configuration Options

Environment variables (all optional except `GEMINI_API_KEY`):

```bash
# Required
GEMINI_API_KEY=your_api_key

# Optional
HOST=0.0.0.0
PORT=8000
SESSION_TIMEOUT_MINUTES=30
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.7
```

## Session Management

- Sessions automatically timeout after 30 minutes of inactivity
- Expired sessions are cleaned up automatically
- Each session maintains full conversation history
- Sessions support multi-turn conversations with context

## Development

### Running in Development Mode

```bash
# With auto-reload
python run_api.py

# Or with uvicorn directly
uvicorn app.main:app --reload --log-level debug
```

### Project Structure Best Practices

- **Separation of Concerns**: Services, models, and API routes are separate
- **Dependency Injection**: FastAPI dependencies for service management
- **Type Safety**: Full type hints with Pydantic models
- **Error Handling**: Consistent error responses across all endpoints
- **Logging**: Comprehensive logging for debugging and monitoring

## Architecture Highlights

### Session-Aware LangGraph Workflow

```
START → session_start_node → conversation_agent_node → END
```

1. **session_start_node**: Initializes/validates session state
2. **conversation_agent_node**: Processes query with full conversation context
3. **LangGraph Checkpointing**: Maintains state between API calls

### Service Layer

- **SessionManager**: Handles session lifecycle and cleanup
- **AgentService**: Manages LangGraph workflows and AI interactions
- **Configuration**: Environment-based settings management

## Error Handling

The API provides consistent error responses:

```json
{
    "error": "Error Type",
    "detail": "Detailed error message",
    "timestamp": 1703123456.789
}
```

Common HTTP status codes:
- `200`: Success
- `404`: Session not found or expired
- `422`: Validation error
- `500`: Internal server error
- `503`: Service unavailable

## Monitoring

- Request logging with timing information
- Session statistics available at `/api/v1/stats`
- Health checks at `/api/v1/health`
- Automatic cleanup of expired resources