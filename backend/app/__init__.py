"""
TayAI Backend Application

A FastAPI application providing AI-powered hair business mentorship.

Package Structure:
    app/
    ├── api/          # API endpoints (FastAPI routers)
    ├── core/         # Configuration, clients, prompt engineering
    │   └── prompts/  # Persona, context detection, prompt generation
    ├── db/           # Database models and connections
    ├── schemas/      # Pydantic request/response models
    ├── services/     # Business logic services
    └── utils/        # Shared utility functions

Usage:
    # Run with uvicorn
    uvicorn app.main:app --reload
    
    # Or use the __main__.py entry point
    python -m app
"""

__version__ = "1.0.0"
