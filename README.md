# TayAI Project

**TayAI** is a custom-trained AI assistant that embodies the voice, expertise, and persona of the TaysLuxe brand owner. Built with cutting-edge RAG (Retrieval-Augmented Generation) architecture, it provides personalized guidance on hair business, vendor sourcing, content creation, and entrepreneurship.

## 🚀 Quick Start

### Local Development

1. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (OpenAI, JWT_SECRET_KEY, etc.)
   ```

2. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Railway Deployment

**🚂 Deploy to Railway (Recommended for Production):**

1. **Create Railway Account** at https://railway.app
2. **Create New Project** → **Add GitHub Repo** → Select this repository
3. **Add PostgreSQL Database**:
   - Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
   - Note the `DATABASE_URL` from the service
4. **Add Redis** (Optional):
   - Click **"+ New"** → **"Database"** → **"Add Redis"**
5. **Deploy Backend**:
   - Click **"+ New"** → **"GitHub Repo"** (same repo)
   - Set **Root Directory:** `backend`
   - Railway will auto-detect Python and use `railway.json` config
6. **Deploy Frontend**:
   - Click **"+ New"** → **"GitHub Repo"** (same repo)
   - Set **Root Directory:** `frontend`
   - Railway will auto-detect Node.js and use `railway.json` config
7. **Configure Environment Variables** (see [Railway Deployment Guide](./RAILWAY_DEPLOYMENT_GUIDE.md))
8. **Run Migrations**:
   ```bash
   railway run --service backend alembic upgrade head
   ```
9. **Enable pgvector Extension**:
   ```bash
   railway run --service backend python -c "from app.db.database import engine; engine.execute('CREATE EXTENSION IF NOT EXISTS vector')"
   ```

**📖 For detailed Railway deployment instructions, see [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md)**

## Project Structure

```
tayai-project/
├── backend/          # FastAPI backend application
│   ├── app/         # Main application code
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # Next.js frontend application
│   ├── app/         # Next.js app directory
│   ├── components/  # React components
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── README.md
└── SETUP.md
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker and Docker Compose (for local development)
- PostgreSQL 14+ with pgvector extension
- Redis 7+ (optional, for rate limiting)
- OpenAI API key with GPT-4 access

## Key Features

### Backend (FastAPI)
- `/api/v1/chat/` - Chat endpoint with RAG
- `/api/v1/auth/login` - User authentication
- `/api/v1/auth/verify` - Token verification
- `/api/v1/usage/` - Usage limits checking
- `/api/v1/admin/knowledge` - Knowledge base management

### Frontend (Next.js)
- Chat widget component with real-time messaging
- Authentication flow
- Usage dashboard
- Admin panel (future)

## Development URLs

- Backend API: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Development Workflow

1. **Week 1**: Discovery & Architecture ✅
2. **Week 2**: Core AI Build (RAG, GPT-4 integration)
3. **Week 3**: Access Control & Interface
4. **Week 4**: Integration & Testing

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Documentation

- **[Railway Deployment Guide](./RAILWAY_DEPLOYMENT_GUIDE.md)** - Complete Railway deployment instructions
- **[Tay AI Specification](./TAY_AI_SPECIFICATION.md)** - Complete behavior, tone, and knowledge base requirements
- **[API Documentation](./API_DOCUMENTATION.md)** - API endpoints and usage (also available at `/docs` when backend is running)
- **[Architecture](./ARCHITECTURE.md)** - System architecture and design
- **[Project Structure](./PROJECT_STRUCTURE.md)** - Codebase organization
- **[Database Schema](./DATABASE_SCHEMA.md)** - Database structure and relationships
- **[Admin Guide](./ADMIN_GUIDE.md)** - Administrative tasks and operations
- **[User Guide](./USER_GUIDE.md)** - End-user documentation
- **[Skool Integration](./SKOOL_INTEGRATION.md)** - Skool platform integration guide
- **[Security Audit](./SECURITY_AUDIT.md)** - Security considerations and best practices

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11+), PostgreSQL with pgvector, Redis
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **AI/ML**: OpenAI GPT-4, Vector embeddings, RAG pipeline
- **Infrastructure**: Docker, Railway (production), Docker Compose (local)
- **Authentication**: JWT tokens, bcrypt password hashing
- **Testing**: pytest, Jest

## 📝 License

See [LICENSE](./LICENSE) file for details.

## 🤝 Support

For questions or issues:
- **Deployment**: See [Railway Deployment Guide](./RAILWAY_DEPLOYMENT_GUIDE.md)
- **API**: See [API Documentation](./API_DOCUMENTATION.md)
- **Admin**: See [Admin Guide](./ADMIN_GUIDE.md)
- Contact the development team for additional support
