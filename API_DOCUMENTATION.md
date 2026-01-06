# TayAI API Documentation

**Base URL:** `http://localhost:8000/api/v1` (development) or `https://api.tayai.com/api/v1` (production)  
**Version:** 1.0  
**Authentication:** Bearer Token (JWT)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Chat Endpoints](#chat-endpoints)
3. [Usage Endpoints](#usage-endpoints)
4. [Admin Endpoints](#admin-endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)

---

## Authentication

### Login

**POST** `/auth/login`

Authenticate user and receive access/refresh tokens.

**Request:**
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=testuser&password=testpass
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Verify Token

**POST** `/auth/verify`

Verify JWT token validity.

**Request:**
```http
POST /api/v1/auth/verify
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "valid": true,
  "user_id": 1,
  "username": "testuser",
  "tier": "basic",
  "is_admin": false
}
```

### Refresh Token

**POST** `/auth/refresh`

Get new access/refresh tokens.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### SSO Login

**POST** `/auth/sso`

Single Sign-On from membership platform.

**Request:**
```json
{
  "platform": "skool",
  "token": "external_platform_token",
  "user_data": {
    "email": "user@example.com",
    "username": "username"
  }
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## Chat Endpoints

### Send Message

**POST** `/chat/`

Send a chat message and receive AI response.

**Request:**
```json
{
  "message": "What is hair porosity?",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?"
    }
  ],
  "include_sources": true
}
```

**Response:**
```json
{
  "response": "Hair porosity refers to how well your hair absorbs and retains moisture...",
  "tokens_used": 150,
  "message_id": 123,
  "sources": [
    {
      "title": "Understanding Hair Porosity",
      "category": "hair_education",
      "score": 0.92,
      "chunk_id": "kb_1_chunk_0"
    }
  ]
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid input
- `401` - Unauthorized
- `403` - Usage limit exceeded
- `429` - Rate limit exceeded

### Stream Message

**POST** `/chat/stream`

Send message and receive streaming response via Server-Sent Events.

**Request:**
```json
{
  "message": "What is hair porosity?",
  "conversation_history": [],
  "include_sources": false
}
```

**Response:** (Server-Sent Events)
```
event: start
data: {"message": "Processing your message...", "context_type": "hair_education"}

event: chunk
data: {"content": "Hair porosity"}

event: chunk
data: {"content": " refers to"}

event: done
data: {"message_id": 123, "tokens_used": 150}
```

### WebSocket Chat

**WebSocket** `/chat/ws`

Real-time bidirectional chat via WebSocket.

**Client → Server:**
```json
{
  "type": "message",
  "content": "Hello",
  "token": "jwt_access_token",
  "conversation_history": []
}
```

**Server → Client:**
```json
{
  "type": "chunk",
  "data": {
    "content": "Hello! How can I help you?"
  }
}
```

### Get Chat History

**GET** `/chat/history?limit=50&offset=0`

Retrieve chat message history.

**Response:**
```json
{
  "messages": [
    {
      "id": 123,
      "role": "user",
      "content": "What is hair porosity?",
      "timestamp": "2024-12-18T10:00:00Z"
    },
    {
      "id": 124,
      "role": "assistant",
      "content": "Hair porosity refers to...",
      "timestamp": "2024-12-18T10:00:01Z"
    }
  ],
  "total_count": 25,
  "has_more": false
}
```

### Clear Chat History

**DELETE** `/chat/history`

Clear all chat history for current user.

**Response:**
```json
{
  "message": "Deleted 25 messages",
  "deleted_count": 25
}
```

---

## Usage Endpoints

### Get Usage Status

**GET** `/usage/`

Get current usage status and limits.

**Response:**
```json
{
  "user_id": 1,
  "tier": "basic",
  "messages_used": 25,
  "messages_limit": 50,
  "tokens_used": 3750,
  "api_cost": 0.1234,
  "period_start": "2024-12-01T00:00:00Z",
  "period_end": "2024-12-31T23:59:59Z",
  "can_send": true,
  "trial_active": true,
  "trial_days_remaining": 3,
  "trial_end_date": "2024-12-21T00:00:00Z"
}
```

---

## Admin Endpoints

### System Overview

**GET** `/admin/stats/overview`

Get system-wide statistics.

**Response:**
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
    "total_usd": 45.67,
    "total_micro_dollars": 45670000
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

Get activity statistics over time.

**Response:**
```json
{
  "daily_stats": [
    {
      "date": "2024-12-18",
      "messages": 150,
      "tokens": 22500
    }
  ],
  "active_users": [
    {
      "date": "2024-12-18",
      "count": 45
    }
  ]
}
```

### Knowledge Base Management

**POST** `/admin/knowledge`

Create knowledge base item.

**Request:**
```json
{
  "title": "Understanding Hair Porosity",
  "content": "Hair porosity refers to...",
  "category": "hair_education",
  "metadata": {
    "source": "course",
    "course_id": 1
  }
}
```

**GET** `/admin/knowledge`

List knowledge base items.

**Query Parameters:**
- `category` - Filter by category
- `active_only` - Only active items (default: true)
- `limit` - Results per page (default: 100)
- `offset` - Pagination offset

**GET** `/admin/knowledge/{item_id}`

Get specific knowledge base item.

**PUT** `/admin/knowledge/{item_id}`

Update knowledge base item.

**DELETE** `/admin/knowledge/{item_id}`

Delete knowledge base item.

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details"
  }
}
```

### Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `AUTHENTICATION_ERROR` | 401 | Authentication required |
| `AUTHORIZATION_ERROR` | 403 | Insufficient permissions |
| `USAGE_LIMIT_EXCEEDED` | 403 | Usage limit reached |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `NOT_FOUND` | 404 | Resource not found |
| `INTERNAL_ERROR` | 500 | Server error |

### Usage Limit Exceeded

```json
{
  "success": false,
  "error": "USAGE_LIMIT_EXCEEDED",
  "message": "Monthly message limit exceeded",
  "details": {
    "current_usage": 50,
    "limit": 50,
    "tier": "basic",
    "upgrade_url": "https://example.com/upgrade",
    "hint": "Upgrade your membership for more messages"
  }
}
```

---

## Rate Limiting

### Rate Limit Headers

All responses include rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
Retry-After: 60
```

### Limits

- **Per Minute:** 60 requests (configurable)
- **Per Hour:** 1000 requests (configurable)
- **Tier Multipliers:**
  - Basic: 1x
  - VIP: 5x

### Rate Limit Exceeded

**Status:** `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "retry_after": 60,
  "limits": {
    "minute_limit": 60,
    "minute_remaining": 0,
    "hour_limit": 1000,
    "hour_remaining": 950
  }
}
```

---

## Webhooks

### Membership Webhook

**POST** `/membership/webhook/{platform}`

Receive membership platform webhooks.

**Supported Platforms:**
- `skool`
- `custom`

**Request:** (Platform-specific format)

**Response:**
```json
{
  "success": true,
  "message": "Webhook processed",
  "user_id": 123,
  "tier": "vip"
}
```

---

## OpenAPI/Swagger Documentation

Interactive API documentation available at:
- **Development:** `http://localhost:8000/docs`
- **Production:** `https://api.tayai.com/docs` (update with your production URL)

---

## SDK Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"  # or your production URL
TOKEN = "your_access_token"

# Send message
response = requests.post(
    f"{BASE_URL}/chat/",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"message": "What is hair porosity?"}
)

print(response.json())
```

### JavaScript

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';  // or your production URL
const token = 'your_access_token';

// Send message
const response = await fetch(`${BASE_URL}/chat/`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: 'What is hair porosity?'
  })
});

const data = await response.json();
console.log(data);
```

---

## Support

For API support:
- **Email:** support@tayai.com (update with your support email)
- **Documentation:** See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) and [README.md](./README.md)
- **Status:** Check your status page (if available)
