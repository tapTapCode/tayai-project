# Railway Environment Variables Template

Use these environment variables when setting up your Railway deployment.

## Backend Service Environment Variables

```bash
# Database (use Railway's PostgreSQL service reference)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (optional - use Railway's Redis service reference if added)
REDIS_URL=${{Redis.REDIS_URL}}

# OpenAI API
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Application Settings
ENVIRONMENT=production
DEBUG=false
API_V1_PREFIX=/api/v1
PROJECT_NAME=TayAI

# CORS (update with your actual domain)
BACKEND_CORS_ORIGINS=["https://ai.taysluxeacademy.com","https://taysluxeacademy.com"]

# Usage Limits
BASIC_MEMBER_MESSAGES_PER_MONTH=50
VIP_MEMBER_MESSAGES_PER_MONTH=1000
TRIAL_PERIOD_DAYS=7

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Port (Railway sets this automatically)
PORT=$PORT
```

## Frontend Service Environment Variables

```bash
# API Configuration (update after backend is deployed)
NEXT_PUBLIC_API_URL=https://your-backend-service.railway.app/api/v1
NEXT_PUBLIC_WS_URL=wss://your-backend-service.railway.app/api/v1

# Base Path (leave empty for subdomain, or set to /ai for subpath)
NEXT_PUBLIC_BASE_PATH=

# Node Environment
NODE_ENV=production

# Port (Railway sets this automatically)
PORT=$PORT
```

## Setup Instructions

1. **Backend Service:**
   - Go to your backend service in Railway
   - Click on **Variables** tab
   - Add each variable from the Backend section above
   - For `DATABASE_URL` and `REDIS_URL`, use Railway's service references: `${{Postgres.DATABASE_URL}}`

2. **Frontend Service:**
   - Go to your frontend service in Railway
   - Click on **Variables** tab
   - Add each variable from the Frontend section above
   - Update `NEXT_PUBLIC_API_URL` with your actual backend service URL after deployment

3. **After Backend is Deployed:**
   - Get your backend service URL from Railway
   - Update frontend `NEXT_PUBLIC_API_URL` to point to: `https://your-backend.railway.app/api/v1`
   - Redeploy frontend service

## Generating JWT Secret Key

```bash
# Generate a secure JWT secret key
openssl rand -hex 32
```

## Notes

- Railway automatically provides `$PORT` environment variable
- Use `${{ServiceName.VARIABLE}}` syntax to reference other Railway services
- Update CORS origins to match your actual domain
- Keep `DEBUG=false` in production
- Never commit actual API keys to git

