# Autonomous AI Document Generation Agent

A multi-agent AI application built with **LangGraph**, **FastAPI**, and **Streamlit** that transforms natural language requests into professional Microsoft Word documents. The system automatically plans a request, executes each task using an LLM, summarizes the results, and generates a downloadable `.docx` report.

## Features

* Multi-agent workflow using LangGraph
* Automatic task planning from user requests
* Sequential LLM-based task execution
* AI-generated professional reports
* Microsoft Word (`.docx`) export
* FastAPI REST API
* Streamlit web interface
* Configurable Groq/OpenAI-compatible models

## Tech Stack

* Python
* LangGraph
* FastAPI
* Streamlit
* Groq API (OpenAI-compatible)
* python-docx
* python-dotenv

## Project Structure

```text
.
├── app.py
├── agent_graph.py
├── document_gen.py
├── streamlit_app.py
├── generated_docs/
├── requirements.txt
└── .env
```

## Workflow

```text
User Request
      │
      ▼
Planner Agent
      │
      ▼
Executor Agent
      │
      ▼
Summarizer Agent
      │
      ▼
Word Document (.docx)
```

## Installation

```bash
git clone <repository-url>
cd autonomous-ai-agent

python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
```

## Running the Application

Start the FastAPI backend:

```bash
uvicorn app:app --reload
```

Start the Streamlit frontend:

```bash
streamlit run streamlit_app.py
```

* FastAPI: `http://localhost:8000`
* API Docs: `http://localhost:8000/docs`
* Streamlit: `http://localhost:8501`

## API Endpoints

| Method | Endpoint               | Description                             |
| ------ | ---------------------- | --------------------------------------- |
| POST   | `/agent`               | Generate a document from a user request |
| GET    | `/download/{filename}` | Download a generated document           |
| GET    | `/health`              | Health check                            |

## Example Request

```json
{
  "request": "Create a business proposal for an AI startup"
}
```

## Future Improvements

* Parallel task execution
* Tool calling (Search, Python, Calculator)
* Persistent memory

## License

This project is intended for educational and portfolio purposes.
