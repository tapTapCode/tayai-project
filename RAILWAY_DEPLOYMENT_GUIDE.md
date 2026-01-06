# Railway Deployment Guide - TayAI

Guide for deploying TayAI on Railway.app platform.

---

## 🤔 Should You Use Railway?

### ✅ Railway is Good For:
- **Easier deployment** - No server management
- **Automatic SSL** - Free SSL certificates
- **Built-in PostgreSQL** - Managed database
- **Environment variables** - Easy configuration
- **Auto-scaling** - Handles traffic spikes
- **Git integration** - Auto-deploy on push
- **Monitoring** - Built-in metrics

### ⚠️ Railway Considerations:
- **Cost** - Can be more expensive than VPS ($5-20+/month)
- **Subpath limitation** - Railway works better with subdomains (`ai.taysluxeacademy.com`) than subpaths (`taysluxeacademy.com/ai`)
- **pgvector support** - Need to verify Railway PostgreSQL supports pgvector extension
- **Less control** - Can't customize server configuration as much

### 💡 Recommendation:

**Use Railway if:**
- You prefer `ai.taysluxeacademy.com` (subdomain) over `taysluxeacademy.com/ai` (subpath)
- You want easier deployment and maintenance
- Budget allows for platform costs ($10-30/month)
- You don't need deep server customization

**Use VPS if:**
- You need `taysluxeacademy.com/ai` (subpath) specifically
- You want more control and lower costs
- You're comfortable with server management
- You need custom Nginx configurations

---

## 🚂 Railway Deployment Option 1: Subdomain (Recommended)

Deploy to `ai.taysluxeacademy.com` (easier with Railway).

### Step 1: Create Railway Account

1. Go to https://railway.app
2. Sign up with GitHub
3. Create new project

### Step 2: Add PostgreSQL Database

1. Click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will create a PostgreSQL instance
3. Note the connection string from the database service

**⚠️ Important:** Check if Railway PostgreSQL supports pgvector:
- Railway uses standard PostgreSQL
- You may need to enable pgvector extension manually
- Or use Railway's plugin system if available

### Step 3: Add Redis (Optional)

1. Click **"+ New"** → **"Database"** → **"Add Redis"**
2. Note the connection URL

### Step 4: Deploy Backend

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your `tayai-project` repository
3. Railway will detect it's a Python project
4. Configure:
   - **Root Directory:** `backend`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Build Command:** `pip install -r requirements.txt`

### Step 5: Configure Backend Environment Variables

In Railway backend service, add:

```bash
# Database (from Railway PostgreSQL service)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (if using Railway Redis)
REDIS_URL=${{Redis.REDIS_URL}}

# OpenAI
OPENAI_API_KEY=sk-proj-your-key-here

# JWT
JWT_SECRET_KEY=<generate-secure-key>

# Application
ENVIRONMENT=production
DEBUG=false
API_V1_PREFIX=/api/v1

# CORS
BACKEND_CORS_ORIGINS=["https://ai.taysluxeacademy.com","https://taysluxeacademy.com"]

# Usage Limits
BASIC_MEMBER_MESSAGES_PER_MONTH=50
VIP_MEMBER_MESSAGES_PER_MONTH=1000
TRIAL_PERIOD_DAYS=7

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

### Step 6: Deploy Frontend

1. Click **"+ New"** → **"GitHub Repo"** (same repo)
2. Configure:
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npm start`
   - **Output Directory:** `.next`

### Step 7: Configure Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=https://your-backend-service.railway.app
NEXT_PUBLIC_WS_URL=wss://your-backend-service.railway.app
NODE_ENV=production
```

### Step 8: Enable pgvector Extension

**Important:** Railway PostgreSQL may not have pgvector by default.

**Option A: Use Railway Plugin (if available)**
- Check Railway marketplace for pgvector plugin

**Option B: Enable via Migration**
```bash
# In Railway backend service, run:
railway run python -c "
from app.db.database import engine
with engine.connect() as conn:
    conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
    conn.commit()
"
```

**Option C: Use Custom PostgreSQL Image**
- Railway allows custom Docker images
- Use `pgvector/pgvector:pg14` image

### Step 9: Run Database Migrations

In Railway backend service:

```bash
railway run alembic upgrade head
```

### Step 10: Configure Custom Domain

1. In Railway project → **Settings** → **Domains**
2. Add custom domain: `ai.taysluxeacademy.com`
3. Railway will provide DNS records to add:
   - CNAME: `ai` → `your-project.railway.app`
4. Add DNS records to your domain provider
5. Railway automatically provisions SSL

### Step 11: Update Frontend API URL

After backend gets custom domain, update frontend env:

```bash
NEXT_PUBLIC_API_URL=https://ai.taysluxeacademy.com/api
NEXT_PUBLIC_WS_URL=wss://ai.taysluxeacademy.com/api
```

Redeploy frontend.

---

## 🚂 Railway Deployment Option 2: Subpath (Advanced)

Deploy to `taysluxeacademy.com/ai` (more complex).

### Challenges:
- Railway doesn't natively support subpath routing
- Need to use Railway's networking or external reverse proxy

### Solution: Use Railway + Cloudflare Workers

1. Deploy backend and frontend to Railway (separate services)
2. Use Cloudflare Workers to route `/ai` path
3. Or use Railway's private networking with external Nginx

**This is more complex - VPS is easier for subpath.**

---

## 📊 Railway vs VPS Comparison

| Feature | Railway | VPS (Nginx) |
|---------|---------|-------------|
| **Ease of Setup** | ⭐⭐⭐⭐⭐ Very Easy | ⭐⭐⭐ Moderate |
| **Cost** | $10-30/month | $5-20/month |
| **Subdomain** | ✅ Easy | ✅ Easy |
| **Subpath (/ai)** | ⚠️ Complex | ✅ Easy |
| **SSL** | ✅ Automatic | ⚠️ Manual (Certbot) |
| **Database** | ✅ Managed | ⚠️ Self-managed |
| **Scaling** | ✅ Auto | ⚠️ Manual |
| **Control** | ⭐⭐ Limited | ⭐⭐⭐⭐⭐ Full |
| **pgvector** | ⚠️ May need setup | ✅ Full control |
| **Maintenance** | ⭐⭐⭐⭐⭐ Minimal | ⭐⭐ More work |

---

## 💰 Railway Pricing Estimate

**Free Tier:**
- $5 credit/month
- Good for testing

**Hobby Plan:**
- ~$5-10/month for small app
- PostgreSQL: ~$5/month
- Redis: ~$5/month (optional)
- **Total: ~$10-20/month**

**Pro Plan:**
- Better for production
- ~$20-50/month depending on usage

---

## 🎯 My Recommendation

**For `taysluxeacademy.com/ai` (subpath):**
- ✅ **Use VPS** - Easier to configure subpath with Nginx
- Follow `PRODUCTION_DEPLOYMENT_GUIDE.md`

**For `ai.taysluxeacademy.com` (subdomain):**
- ✅ **Use Railway** - Much easier deployment
- Follow this guide

**Best of Both Worlds:**
- Deploy to Railway for easier management
- Use Cloudflare Workers or external Nginx to route `/ai` path
- More complex but gives you Railway benefits + subpath

---

## 🚀 Quick Railway Setup (Subdomain)

If you choose Railway with subdomain:

1. **Create Railway project**
2. **Add PostgreSQL** (check pgvector support)
3. **Deploy backend** from `backend/` directory
4. **Deploy frontend** from `frontend/` directory
5. **Set environment variables** (see Step 5 above)
6. **Run migrations:** `railway run alembic upgrade head`
7. **Add custom domain:** `ai.taysluxeacademy.com`
8. **Done!**

---

## ❓ Need Help Deciding?

**Choose Railway if:**
- You want `ai.taysluxeacademy.com` (subdomain is fine)
- You prefer easy deployment over cost savings
- You don't want to manage servers
- Budget allows $10-30/month

**Choose VPS if:**
- You need `taysluxeacademy.com/ai` (subpath required)
- You want lower costs ($5-10/month)
- You're comfortable with server management
- You need full control

---

## 📝 Next Steps

1. **Decide:** Subdomain (Railway) or Subpath (VPS)?
2. **If Railway:** Follow this guide
3. **If VPS:** Follow `PRODUCTION_DEPLOYMENT_GUIDE.md`

Want me to create a Railway-specific docker-compose or configuration files?

