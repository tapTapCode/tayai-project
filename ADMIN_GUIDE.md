# TayAI Admin Guide

Complete guide for administrators managing the TayAI platform.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Management](#user-management)
3. [Knowledge Base Management](#knowledge-base-management)
4. [Analytics & Reporting](#analytics--reporting)
5. [System Configuration](#system-configuration)
6. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing Admin Panel

1. **Login as Admin:**
   - Use admin credentials to login at `/api/v1/auth/login`
   - Admin users have `is_admin: true` flag

2. **Admin Endpoints:**
   - All admin endpoints are under `/api/v1/admin/*`
   - Require admin authentication token

3. **API Documentation:**
   - Interactive docs: `http://localhost:8000/docs`
   - Full API reference: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

---

## User Management

### View All Users

**GET** `/admin/users`

```bash
curl -X GET "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response:**
```json
[
  {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "tier": "basic",
    "is_active": true,
    "created_at": "2024-12-01T00:00:00Z"
  }
]
```

### View User Details

**GET** `/admin/users/{user_id}`

View detailed user information including:
- Profile data
- Usage statistics
- Activity history
- Membership status

### View User Activity

**GET** `/admin/users/{user_id}/activity`

Get user's chat activity:
- Recent messages
- Message count
- Token usage
- API costs

### View User Usage

**GET** `/admin/users/{user_id}/usage`

Get detailed usage statistics:
- Messages sent this month
- Tokens consumed
- API costs
- Usage limits

---

## Knowledge Base Management

### Create Knowledge Item

**POST** `/admin/knowledge`

```json
{
  "title": "Understanding Hair Porosity",
  "content": "Hair porosity refers to how well your hair absorbs and retains moisture...",
  "category": "hair_education",
  "metadata": {
    "source": "course",
    "course_id": 1
  }
}
```

**Features:**
- Content automatically chunked
- Embedded using OpenAI
- Indexed in Pinecone
- Available for RAG retrieval

### List Knowledge Items

**GET** `/admin/knowledge?category=hair_education&active_only=true&limit=100`

**Query Parameters:**
- `category` - Filter by category
- `active_only` - Only active items (default: true)
- `limit` - Results per page (1-500)
- `offset` - Pagination offset

### Update Knowledge Item

**PUT** `/admin/knowledge/{item_id}`

Update existing knowledge base item. Content is automatically re-indexed.

### Delete Knowledge Item

**DELETE** `/admin/knowledge/{item_id}`

Deletes item from database and Pinecone index.

### Bulk Upload

**POST** `/admin/knowledge/bulk`

Upload multiple knowledge items at once.

**Request:**
```json
{
  "items": [
    {
      "title": "Item 1",
      "content": "Content 1",
      "category": "hair_education"
    },
    {
      "title": "Item 2",
      "content": "Content 2",
      "category": "business_mentorship"
    }
  ]
}
```

### Reindex All

**POST** `/admin/knowledge/reindex`

Reindex all knowledge base items in Pinecone. Useful after:
- Pinecone index changes
- Embedding model updates
- Data corruption recovery

### Semantic Search

**POST** `/admin/knowledge/search`

Search knowledge base semantically.

**Request:**
```json
{
  "query": "hair porosity test",
  "top_k": 10,
  "score_threshold": 0.7
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "title": "Understanding Hair Porosity",
      "score": 0.92,
      "content": "..."
    }
  ],
  "total": 1
}
```

### Knowledge Base Statistics

**GET** `/admin/knowledge/stats`

Get knowledge base statistics:
- Total items
- Active items
- Categories count
- Index statistics

---

## Analytics & Reporting

### System Overview

**GET** `/admin/stats/overview`

Get comprehensive system statistics:
- User counts (total, active, by tier)
- Message statistics (total, today, this week)
- Token usage
- API costs
- Knowledge base stats

**Example Response:**
```json
{
  "users": {
    "total": 150,
    "active": 120,
    "by_tier": {
      "basic": 100,
      "vip": 50
    }
  },
  "messages": {
    "total": 5000,
    "today": 150,
    "this_week": 800
  },
  "tokens": {
    "total_used": 750000
  },
  "api_costs": {
    "total_usd": 45.67
  },
  "knowledge_base": {
    "total_items": 50,
    "active_items": 48,
    "categories_count": 5
  }
}
```

### Activity Statistics

**GET** `/admin/stats/activity?days=7`

Get activity trends over time:
- Daily message counts
- Daily token usage
- Active users per day

**Query Parameters:**
- `days` - Number of days (1-30, default: 7)

### Top Users

**GET** `/admin/stats/top-users?limit=10&period=month`

Get most active users:
- By message count
- By token usage
- By API costs

**Query Parameters:**
- `limit` - Number of users (default: 10)
- `period` - Time period (day, week, month)

---

## System Configuration

### Environment Variables

Key configuration variables (see `.env.example`):

**Authentication:**
- `JWT_SECRET_KEY` - Secret for token signing
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration (default: 30)

**Usage Limits:**
- `BASIC_MEMBER_MESSAGES_PER_MONTH` - Basic tier limit (default: 50)
- `VIP_MEMBER_MESSAGES_PER_MONTH` - VIP tier limit (default: 1000)
- `TRIAL_PERIOD_DAYS` - Trial period (default: 7)

**Rate Limiting:**
- `RATE_LIMIT_PER_MINUTE` - Requests per minute (default: 60)
- `RATE_LIMIT_PER_HOUR` - Requests per hour (default: 1000)

**API Keys:**
- `OPENAI_API_KEY` - OpenAI API key
- `PINECONE_API_KEY` - Pinecone API key
- `REDIS_URL` - Redis connection URL

### Updating Configuration

1. **Edit `.env` file** with new values
2. **Restart services:**
   ```bash
   docker-compose restart backend
   ```

### Persona Configuration

**Test Persona:**

**POST** `/admin/persona/test`

Test persona responses with custom messages.

**Request:**
```json
{
  "message": "How should I price my services?",
  "context_type": "business_mentorship",
  "user_tier": "basic"
}
```

**Get Context Types:**

**GET** `/admin/persona/context-types`

Get available conversation context types.

---

## Troubleshooting

### Common Issues

#### 1. Users Can't Send Messages

**Check:**
- Usage limits: `GET /admin/users/{user_id}/usage`
- Trial status for Basic tier users
- Rate limiting: Check rate limit headers

**Solution:**
- Increase limits if needed
- Extend trial period
- Adjust rate limits

#### 2. Knowledge Base Not Returning Results

**Check:**
- Knowledge base stats: `GET /admin/knowledge/stats`
- Pinecone index status
- Embedding model configuration

**Solution:**
- Reindex: `POST /admin/knowledge/reindex`
- Check Pinecone API key
- Verify content is active

#### 3. High API Costs

**Check:**
- System overview: `GET /admin/stats/overview`
- Per-user costs: `GET /admin/users/{user_id}/usage`
- Token usage patterns

**Solution:**
- Review token usage
- Optimize prompts
- Adjust max_tokens settings

#### 4. Authentication Issues

**Check:**
- JWT secret key configuration
- Token expiration settings
- User active status

**Solution:**
- Verify JWT_SECRET_KEY is set
- Check token expiration
- Ensure user is active

### Monitoring

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Service Status:**
- Database: Check PostgreSQL connection
- Redis: Check Redis connection
- Pinecone: Check index status
- OpenAI: Check API key validity

### Logs

**View Backend Logs:**
```bash
docker-compose logs -f backend
```

**View Frontend Logs:**
```bash
docker-compose logs -f frontend
```

**View All Logs:**
```bash
docker-compose logs -f
```

---

## Best Practices

### Knowledge Base

1. **Organize by Category:**
   - Use consistent categories
   - Tag related content

2. **Keep Content Updated:**
   - Regular content reviews
   - Update outdated information
   - Remove inactive items

3. **Optimize Content:**
   - Clear, concise content
   - Proper formatting
   - Relevant metadata

### User Management

1. **Monitor Usage:**
   - Regular usage reviews
   - Identify power users
   - Track engagement

2. **Tier Management:**
   - Appropriate tier assignments
   - Trial period monitoring
   - Upgrade prompts

### System Maintenance

1. **Regular Backups:**
   - Database backups
   - Knowledge base exports
   - Configuration backups

2. **Performance Monitoring:**
   - API response times
   - Database query performance
   - Cache hit rates

3. **Security:**
   - Regular security audits
   - Token rotation
   - Access review

---

## Support

For admin support:
- **Email:** admin@tayai.com (update with your admin email)
- **Documentation:** See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Issues:** Create GitHub issue or contact development team

---

## Quick Reference

### Common Commands

```bash
# View all users
curl -X GET "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer TOKEN"

# View system stats
curl -X GET "http://localhost:8000/api/v1/admin/stats/overview" \
  -H "Authorization: Bearer TOKEN"

# Reindex knowledge base
curl -X POST "http://localhost:8000/api/v1/admin/knowledge/reindex" \
  -H "Authorization: Bearer TOKEN"

# View user activity
curl -X GET "http://localhost:8000/api/v1/admin/users/1/activity" \
  -H "Authorization: Bearer TOKEN"
```
