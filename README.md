# Agentic Software Developer - Backend

This is the backend for the **Agentic Software Developer** application. The project serves as an AI-powered coding assistant, designed to facilitate full-stack development through conversational commands, file generation, and real-time WebSocket interactions.

## 🚀 Features

- **FastAPI-driven API**: Highly performant, async-ready REST API built with FastAPI.
- **Real-time Chat with LangGraph**: Integration with LangChain/LangGraph allowing an AI orchestration agent to handle complex queries, track memory, and respond dynamically.
- **WebSocket Streaming**: Instantaneous feedback generation and chat via WebSocket (`ws://<host>/api/ws/chat`).
- **File & Project Management**: Endpoints to manage workspaces, read, update, and overwrite generated code files (e.g., `projects/{project_id}/files`).
- **Execution & QA Integration**: Routes designed to execute and test the generated code automatically.

## 📂 Project Structure

```bash
backend/
├── app/
│   ├── api/                 # API endpoints and route definitions
│   │   ├── routes.py        # Main router registry
│   │   ├── files.py         # Handles file system operations within workspaces
│   │   ├── projects.py      # Manages project boundaries
│   │   ├── memory.py        # Logic for RAG and agent memory
│   │   ├── execution.py     # Code execution strategies
│   │   └── websocket.py     # Real-time WebSockets integration
│   ├── chatbot/             # Conversational routing logic
│   ├── graph/
│   │   └── workflow.py      # LangGraph orchestration state machine
│   └── main.py              # Application entry point, CORS and FastAPI configuration
├── projects_generated/      # Generated code workspaces (Ignored in Version Control)
├── requirements.txt         # Python Dependencies
├── .gitignore               # Standard Git Ignore configurations
└── README.md                # Project Documentation
```

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/maviyashaikh25/agentic_sd_backend.git
   cd agentic_sd_backend
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: Ensure you add core dependencies such as `fastapi`, `uvicorn`, `langchain`, `langgraph`, and `pydantic` if not present.*

4. **Set Environment Variables:**
   Create a `.env` file in the root directory to store your API keys and parameters securely.
   ```ini
   # .env
   GROQ_API_KEY=your_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

5. **Start the Development Server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 🔌 API Endpoints (Overview)

The server boots up with Swagger UI by default. Access the comprehensive documentation at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Key Routes
- `GET /health` : Check API health status.
- `WS /api/ws/chat` : Establish LangGraph WebSocket chat connection.
- `GET /api/projects/{project_id}/files/` : Retrieve the file tree for a generated project.
- `PUT /api/projects/{project_id}/files/{filepath}` : Manually edit or update the AI generated files.

## 🛡️ License

All rights reserved.
