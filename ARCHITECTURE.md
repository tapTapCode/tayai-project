# TayAI System Architecture Diagram

## High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        User[👤 User]
        Browser[🌐 Web Browser]
    end

    subgraph "Frontend Layer"
        NextJS[⚛️ Next.js Frontend<br/>Port: 3000]
        ChatWidget[💬 ChatWidget Component]
        AuthContext[🔐 AuthContext]
        APIClient[📡 API Client<br/>axios]
    end

    subgraph "Backend Layer - FastAPI"
        FastAPI[🚀 FastAPI Backend<br/>Port: 8000]
        
        subgraph "API Endpoints"
            AuthEP[🔑 /api/v1/auth]
            ChatEP[💬 /api/v1/chat]
            UsageEP[📊 /api/v1/usage]
            AdminEP[👨‍💼 /api/v1/admin]
        end
        
        subgraph "Middleware"
            CORS[CORS Middleware]
            TrustedHost[Trusted Host]
            AuthDeps[Authentication Dependencies]
        end
        
        subgraph "Service Layer"
            ChatService[ChatService]
            RAGService[RAGService]
            UserService[UserService]
            UsageService[UsageService]
            KnowledgeService[KnowledgeService]
        end
        
        subgraph "Core Components"
            Security[Security Utils<br/>JWT, Bcrypt]
            Config[Configuration<br/>Settings]
        end
    end

    subgraph "Data Layer"
        PostgreSQL[(🗄️ PostgreSQL<br/>Port: 5432)]
        Redis[(⚡ Redis<br/>Port: 6379)]
    end

    subgraph "External Services"
        OpenAI[🤖 OpenAI API<br/>GPT-4, Embeddings]
        Pinecone[🔍 Pinecone<br/>Vector Database]
    end

    User --> Browser
    Browser --> NextJS
    NextJS --> ChatWidget
    NextJS --> AuthContext
    ChatWidget --> APIClient
    AuthContext --> APIClient
    
    APIClient --> FastAPI
    FastAPI --> CORS
    CORS --> TrustedHost
    TrustedHost --> AuthEP
    TrustedHost --> ChatEP
    TrustedHost --> UsageEP
    TrustedHost --> AdminEP
    
    AuthEP --> AuthDeps
    ChatEP --> AuthDeps
    UsageEP --> AuthDeps
    AdminEP --> AuthDeps
    
    AuthDeps --> Security
    AuthDeps --> UserService
    
    ChatEP --> ChatService
    ChatService --> RAGService
    ChatService --> UsageService
    ChatService --> PostgreSQL
    
    RAGService --> OpenAI
    RAGService --> Pinecone
    
    UsageService --> PostgreSQL
    UserService --> PostgreSQL
    KnowledgeService --> PostgreSQL
    KnowledgeService --> RAGService
    
    AdminEP --> KnowledgeService
    
    Config --> FastAPI
    Security --> Config
    
    style User fill:#e1f5ff
    style NextJS fill:#61dafb
    style FastAPI fill:#009688
    style PostgreSQL fill:#336791
    style Redis fill:#dc382d
    style OpenAI fill:#412991
    style Pinecone fill:#5cceee
```

## Detailed Component Architecture

### Backend Service Layer

```mermaid
graph LR
    subgraph "Chat Flow"
        A[Chat Endpoint] --> B[Usage Check]
        B --> C[ChatService.process_message]
        C --> D[RAGService.retrieve_context]
        D --> E[OpenAI Embeddings]
        E --> F[Pinecone Query]
        F --> G[Context Retrieval]
        G --> C
        C --> H[OpenAI GPT-4]
        H --> I[Save to DB]
        I --> J[Track Usage]
    end
    
    subgraph "Authentication Flow"
        K[Auth Endpoint] --> L[UserService]
        L --> M[Verify Password]
        M --> N[Create JWT]
        N --> O[Return Token]
    end
    
    subgraph "Knowledge Base Flow"
        P[Admin Endpoint] --> Q[KnowledgeService]
        Q --> R[Generate Embedding]
        R --> S[Store in Pinecone]
        S --> T[Save Metadata in PostgreSQL]
    end
```
        
## Data Flow Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant API as FastAPI
    participant CS as ChatService
    participant RS as RAGService
    participant OAI as OpenAI
    participant PC as Pinecone
    participant DB as PostgreSQL
    participant US as UsageService

    U->>F: Send Message
    F->>API: POST /api/v1/chat
    API->>US: Check Usage Limits
    US->>DB: Query Usage Tracking
    DB-->>US: Usage Data
    US-->>API: Usage Status
    
    API->>CS: process_message()
    CS->>RS: retrieve_context(query)
    RS->>OAI: Generate Embedding
    OAI-->>RS: Embedding Vector
    RS->>PC: Query Vector DB
    PC-->>RS: Relevant Context
    RS-->>CS: Context String
    
    CS->>CS: Build Messages with Context
    CS->>OAI: Chat Completion Request
    OAI-->>CS: AI Response + Tokens
    CS->>DB: Save Chat Message
    CS->>US: Record Usage
    US->>DB: Update Usage Tracking
    CS-->>API: ChatResponse
    API-->>F: JSON Response
    F-->>U: Display Message
```

## Database Schema

```mermaid
erDiagram
    User ||--o{ ChatMessage : "has many"
    User ||--o{ UsageTracking : "has many"
    KnowledgeBase ||--o| Pinecone : "indexed in"
    
    User {
        int id PK
        string email UK
        string username UK
        string hashed_password
        enum tier
        boolean is_active
        boolean is_admin
        datetime created_at
        datetime updated_at
    }
    
    ChatMessage {
        int id PK
        int user_id FK
        text message
        text response
        int tokens_used
        datetime created_at
    }
    
    UsageTracking {
        int id PK
        int user_id FK
        datetime period_start
        datetime period_end
        int messages_count
        int tokens_used
        datetime created_at
    }
    
    KnowledgeBase {
        int id PK
        string title
        text content
        string category
        text metadata
        string pinecone_id UK
        boolean is_active
        datetime created_at
        datetime updated_at
    }
```

## Technology Stack

### Frontend
- **Framework**: Next.js (React)
- **Language**: TypeScript
- **HTTP Client**: Axios
- **State Management**: React Context (AuthContext)
- **Styling**: Tailwind CSS

### Backend
- **Framework**: FastAPI (Python)
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy (Async)
- **Authentication**: JWT (OAuth2)
- **Password Hashing**: Bcrypt

### Database & Storage
- **Primary DB**: PostgreSQL 14+
- **Cache**: Redis 7+
- **Vector DB**: Pinecone

### External Services
- **AI Model**: OpenAI GPT-4
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector Search**: Pinecone

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **API Documentation**: FastAPI Auto-generated (Swagger/OpenAPI)

## API Endpoints Structure

```mermaid
graph TD
    API[FastAPI App] --> Router[API Router /api/v1]
    
    Router --> Auth[/auth]
    Router --> Chat[/chat]
    Router --> Usage[/usage]
    Router --> Admin[/admin]
    
    Auth --> Login[POST /login]
    Auth --> Verify[POST /verify]
    
    Chat --> SendMessage[POST /]
    Chat --> History[GET /history]
    
    Usage --> Status[GET /]
    
    Admin --> Knowledge[GET/POST /knowledge]
    Admin --> KnowledgeItem[GET/PUT/DELETE /knowledge/:id]
```

## Security Architecture

```mermaid
graph TB
    Request[HTTP Request] --> CORS[CORS Middleware]
    CORS --> TrustedHost{Trusted Host?}
    TrustedHost -->|No| Reject[Reject Request]
    TrustedHost -->|Yes| AuthCheck{Protected Endpoint?}
    
    AuthCheck -->|No| Public[Public Access]
    AuthCheck -->|Yes| TokenCheck{Has JWT Token?}
    
    TokenCheck -->|No| Unauthorized[401 Unauthorized]
    TokenCheck -->|Yes| VerifyToken[Verify JWT Token]
    
    VerifyToken -->|Invalid| Unauthorized
    VerifyToken -->|Valid| UserCheck{User Active?}
    
    UserCheck -->|No| Forbidden[403 Forbidden]
    UserCheck -->|Yes| AdminCheck{Admin Endpoint?}
    
    AdminCheck -->|Yes| IsAdmin{Is Admin?}
    AdminCheck -->|No| Process[Process Request]
    
    IsAdmin -->|No| Forbidden
    IsAdmin -->|Yes| Process
    
    Process --> Response[HTTP Response]
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Docker Compose Environment"
        subgraph "Services"
            Frontend[Frontend Container<br/>Next.js :3000]
            Backend[Backend Container<br/>FastAPI :8000]
            Postgres[PostgreSQL Container<br/>:5432]
            Redis[Redis Container<br/>:6379]
        end
        
        subgraph "Volumes"
            PostgresData[(postgres_data)]
            RedisData[(redis_data)]
        end
    end
    
    subgraph "External Services"
        OpenAI[OpenAI API<br/>Cloud]
        Pinecone[Pinecone<br/>Cloud]
    end
    
    Frontend --> Backend
    Backend --> Postgres
    Backend --> Redis
    Backend --> OpenAI
    Backend --> Pinecone
    
    Postgres --> PostgresData
    Redis --> RedisData
```

## Key Architectural Patterns

1. **Layered Architecture**: Clear separation between API, Service, and Data layers
2. **Dependency Injection**: FastAPI's dependency system for authentication and database sessions
3. **RAG (Retrieval-Augmented Generation)**: Combines vector search with LLM for context-aware responses
4. **JWT Authentication**: Stateless authentication with token-based access control
5. **Async/Await**: Full async support for I/O operations (database, API calls)
6. **Service-Oriented**: Business logic encapsulated in service classes
7. **Repository Pattern**: Database access abstracted through SQLAlchemy models

## Data Flow Summary

1. **User Authentication**: User credentials → JWT token generation → Token stored in localStorage
2. **Chat Request**: User message → Usage validation → RAG context retrieval → OpenAI API call → Response storage
3. **Knowledge Base Management**: Admin uploads content → Embedding generation → Pinecone indexing → Metadata storage
4. **Usage Tracking**: Every chat request → Token usage recorded → Monthly limits enforced

