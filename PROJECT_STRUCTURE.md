# TayAI Project Structure

This document explains the project structure and how components are organized.

## Overview

The TayAI project follows a clean architecture pattern with clear separation between:
- **Backend**: FastAPI application handling business logic, AI integration, and data persistence
- **Frontend**: Next.js application providing the user interface
- **Infrastructure**: Docker Compose for local development

## Backend Structure (`backend/`)

### `app/` - Main Application

```
app/
├── __init__.py          # Package info and version
├── __main__.py          # CLI entry point
├── main.py              # FastAPI application entry point
├── dependencies.py      # Shared dependencies (auth, database)
│
├── api/                 # API routes
│   └── v1/
│       ├── router.py    # Main API router
│       └── endpoints/   # Individual endpoint modules
│           ├── admin.py     # Admin & knowledge management
│           ├── auth.py      # Authentication endpoints
│           ├── chat.py      # Chat endpoints
│           └── usage.py     # Usage tracking endpoints
│
├── core/                # Core configuration and utilities
│   ├── __init__.py      # Core module exports
│   ├── clients.py       # Shared OpenAI/Pinecone clients
│   ├── config.py        # Application settings (.env loading)
│   ├── security.py      # JWT and password hashing
│   └── prompts/         # Prompt engineering system
│       ├── __init__.py      # Package exports
│       ├── persona.py       # PersonaConfig, DEFAULT_PERSONA
│       ├── context.py       # ConversationContext, detection
│       ├── generation.py    # System prompt builders
│       └── fallbacks.py     # Fallback responses
│
├── db/                  # Database layer
│   ├── __init__.py
│   ├── database.py      # Database connection and session
│   └── models.py        # SQLAlchemy models
│
├── schemas/             # Pydantic schemas (request/response)
│   ├── __init__.py      # Schema exports
│   ├── auth.py          # Token, UserLogin schemas
│   ├── chat.py          # ChatRequest, ChatResponse
│   ├── knowledge.py     # Knowledge base schemas
│   └── usage.py         # Usage tracking schemas
│
├── services/            # Business logic layer
│   ├── __init__.py      # Service exports
│   ├── chat_service.py      # Chat and AI processing
│   ├── knowledge_service.py # Knowledge base management
│   ├── rag_service.py       # RAG (embeddings, vector search)
│   ├── usage_service.py     # Usage tracking and limits
│   └── user_service.py      # User operations
│
└── utils/               # Shared utility functions
    ├── __init__.py      # Utility exports
    └── text.py          # Text manipulation (truncate, sanitize)
```

### `scripts/` - Utility Scripts

```
scripts/
├── __init__.py
├── import_content.py        # Import custom content from content/
├── init_pinecone.py         # Pinecone index management
└── seed_knowledge_base.py   # Initial knowledge base seeding
```

### `tests/` - Automated Tests

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and mocks
├── unit/                    # Unit tests (isolated)
│   ├── test_prompts.py      # Prompt engineering tests
│   ├── test_context.py      # Context detection tests
│   ├── test_utils.py        # Utility function tests
│   ├── test_schemas.py      # Schema validation tests
│   └── test_rag_service.py  # RAG service tests
└── integration/             # Integration tests
    └── test_api.py          # API endpoint tests
```

## Frontend Structure (`frontend/`)

```
frontend/
├── app/                 # Next.js App Directory
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles
│
├── components/          # React Components
│   ├── __init__.ts
│   └── ChatWidget.tsx   # Main chat interface
│
├── contexts/            # React Contexts
│   ├── __init__.ts
│   └── AuthContext.tsx  # Authentication state
│
└── lib/                 # Utilities
    └── api.ts           # API client
```

## Content Directory (`content/`)

Custom knowledge base content for TayAI:

```
content/
├── README.md            # Content authoring guide
├── faqs.yaml            # Frequently asked questions
├── frameworks.yaml      # Business frameworks
├── quick_tips.yaml      # Quick tips
└── courses/             # Course transcripts
    ├── README.md        # Course format guide
    └── _example-course.md  # Example template
```

## Configuration Files

### Root Level
- `.env.example` - Environment variable template
- `.gitignore` - Git ignore rules
- `docker-compose.yml` - Docker services
- `README.md` - Project overview
- `SETUP.md` - Setup instructions
- `ARCHITECTURE.md` - System architecture
- `DATABASE_SCHEMA.md` - Database design
- `TAY_AI_SPECIFICATION.md` - Complete AI specification and behavior requirements

### Backend
- `requirements.txt` - Python dependencies
- `Dockerfile` - Backend container
- `alembic.ini` - Database migrations
- `pytest.ini` - Test configuration

### Frontend
- `package.json` - Node.js dependencies
- `Dockerfile` - Frontend container
- `tsconfig.json` - TypeScript config
- `tailwind.config.js` - Tailwind CSS
- `next.config.js` - Next.js config

## Key Design Patterns

### 1. Layered Architecture
- **API Layer**: FastAPI routers handle HTTP
- **Service Layer**: Business logic (ChatService, RAGService)
- **Data Layer**: SQLAlchemy models, Pinecone

### 2. Dependency Injection
- Database sessions via `get_db()`
- Current user via `get_current_user()`
- Shared clients via `get_openai_client()`, `get_pinecone_index()`

### 3. Module Exports
- Each package has `__init__.py` with `__all__` exports
- Clean imports: `from app.schemas import ChatResponse`
- Centralized configuration: `from app.core import settings`

## Data Flow

### Chat Request Flow
1. User sends message via frontend
2. `POST /api/v1/chat/` received by FastAPI
3. `ChatService.process_message()`:
   - Detect conversation context
   - Retrieve RAG context from Pinecone
   - Build system prompt with persona
   - Call OpenAI GPT-4
   - Save to PostgreSQL
4. Return response to frontend

### RAG Pipeline
1. User query received
2. Generate embedding via OpenAI
3. Query Pinecone for similar vectors
4. Filter by relevance score
5. Format context for prompt injection
6. Include in GPT-4 system message

## Running Tests

```bash
cd backend

# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/unit/test_prompts.py -v

# Run with coverage
python3 -m pytest tests/ --cov=app --cov-report=term-missing
```
