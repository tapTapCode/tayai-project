# How to Run TayAI Project

Complete guide for running the TayAI project locally and in production.

## Prerequisites

- **Python 3.11+** - For backend
- **Node.js 20+** - For frontend
- **Docker & Docker Compose** - For local development (recommended)
- **PostgreSQL 14+ with pgvector** - Database
- **Redis 7+** - For rate limiting (optional)
- **OpenAI API Key** - For GPT-4 and embeddings

---

## Option 1: Docker Compose (Recommended for Local Development)

### Step 1: Clone the Repository

```bash
git clone https://github.com/TaysLuxe/tayai-project.git
cd tayai-project
```

### Step 2: Create Environment File

Create a `.env` file in the root directory:

```bash
# Database
POSTGRES_USER=tayai_user
POSTGRES_PASSWORD=tayai_password
POSTGRES_DB=tayai_db
DATABASE_URL=postgresql://tayai_user:tayai_password@postgres:5432/tayai_db

# Redis
REDIS_URL=redis://redis:6379

# OpenAI API
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Step 3: Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Frontend (port 3000)

### Step 4: Run Database Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Step 5: Enable pgvector Extension

```bash
docker-compose exec postgres psql -U tayai_user -d tayai_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 6: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart a specific service
docker-compose restart backend

# Execute commands in containers
docker-compose exec backend python -m app
docker-compose exec frontend npm run build
```

---

## Option 2: Manual Setup (Without Docker)

### Backend Setup

#### Step 1: Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 3: Set Up Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
DATABASE_URL=postgresql://tayai_user:tayai_password@localhost:5432/tayai_db
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
JWT_SECRET_KEY=your-super-secret-jwt-key
ENVIRONMENT=development
DEBUG=true
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

#### Step 4: Set Up PostgreSQL

1. Install PostgreSQL 14+ with pgvector extension
2. Create database:
   ```bash
   createdb tayai_db
   psql tayai_db -c "CREATE EXTENSION vector;"
   ```

#### Step 5: Run Migrations

```bash
alembic upgrade head
```

#### Step 6: Start Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the module:
```bash
python -m app
```

Backend will be available at: http://localhost:8000

---

### Frontend Setup

#### Step 1: Install Dependencies

```bash
cd frontend
npm install
```

#### Step 2: Set Up Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

#### Step 3: Start Development Server

```bash
npm run dev
```

Frontend will be available at: http://localhost:3000

#### Step 4: Build for Production

```bash
npm run build
npm start
```

---

## Option 3: Railway Deployment (Production)

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub
3. Create a new project

### Step 2: Add PostgreSQL Database

1. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Note the `DATABASE_URL` from the service variables

### Step 3: Add Redis (Optional)

1. Click **"+ New"** → **"Database"** → **"Add Redis"**
2. Note the `REDIS_URL`

### Step 4: Deploy Backend

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repository
3. Configure:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Build Command**: `pip install -r requirements.txt`

4. Add Environment Variables:
   ```bash
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   OPENAI_API_KEY=your-key-here
   JWT_SECRET_KEY=your-secret-key
   ENVIRONMENT=production
   DEBUG=false
   BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]
   ```

5. Run migrations:
   ```bash
   railway run --service backend alembic upgrade head
   ```

6. Enable pgvector:
   ```bash
   railway run --service backend python -c "from app.db.database import engine; engine.execute('CREATE EXTENSION IF NOT EXISTS vector')"
   ```

### Step 5: Deploy Frontend

1. Click **"+ New"** → **"GitHub Repo"** (same repo)
2. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm start`

3. Add Environment Variables:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend-service.up.railway.app/api/v1
   NEXT_PUBLIC_WS_URL=wss://your-backend-service.up.railway.app/api/v1
   NODE_ENV=production
   ```

### Step 6: Update Backend CORS

Update `BACKEND_CORS_ORIGINS` in backend service to include your frontend URL.

---

## Generating JWT Secret Key

```bash
openssl rand -hex 32
```

---

## Testing the Setup

### Backend Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-07T12:00:00"
}
```

### Backend API Docs

Visit: http://localhost:8000/docs

### Frontend

1. Open http://localhost:3000
2. Login with test credentials (create user first via `/api/v1/auth/register`)
3. Test the chat interface

---

## Common Issues

### Issue: Database Connection Failed

**Solution:**
- Check PostgreSQL is running: `docker-compose ps` or `pg_isready`
- Verify `DATABASE_URL` in `.env` file
- Ensure pgvector extension is installed

### Issue: Frontend Can't Connect to Backend

**Solution:**
- Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Verify backend is running on port 8000
- Check CORS settings in backend

### Issue: OpenAI API Errors

**Solution:**
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has GPT-4 access
- Ensure sufficient API credits

### Issue: Port Already in Use

**Solution:**
- Change ports in `docker-compose.yml`
- Or stop conflicting services:
  ```bash
  # Find process using port 8000
  lsof -i :8000
  # Kill process
  kill -9 <PID>
  ```

---

## Development Workflow

1. **Make code changes**
2. **Backend**: Auto-reloads with `--reload` flag
3. **Frontend**: Hot-reloads automatically in dev mode
4. **Database**: Run migrations when schema changes:
   ```bash
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

---

## Production Checklist

Before deploying to production:

- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Use strong `JWT_SECRET_KEY`
- [ ] Configure proper `BACKEND_CORS_ORIGINS`
- [ ] Set up SSL/HTTPS
- [ ] Configure database backups
- [ ] Set up monitoring and logging
- [ ] Review security settings
- [ ] Test all endpoints
- [ ] Load test the application

---

For more details, see:
- [Railway Deployment Guide](./RAILWAY_DEPLOYMENT_GUIDE.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Admin Guide](./ADMIN_GUIDE.md)

