"""
RAG Service - Retrieval-Augmented Generation

Handles the core RAG pipeline:
1. Content chunking and embedding generation
2. Vector storage in PostgreSQL with pgvector
3. Semantic search and context retrieval
"""
import re
import logging
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass, field
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, delete
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import settings
from app.core.clients import get_openai_client
from app.db.models import VectorEmbedding

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ChunkConfig:
    """Configuration for content chunking."""
    chunk_size: int = 500
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    separators: List[str] = field(default_factory=lambda: ["\n\n", "\n", ". "])


@dataclass
class RetrievalResult:
    """Single result from context retrieval."""
    content: str
    score: float
    metadata: Dict
    chunk_id: str


@dataclass
class ContextResult:
    """Complete context retrieval result with sources."""
    context: str
    sources: List[Dict]
    total_matches: int
    average_score: float


# =============================================================================
# RAG Service
# =============================================================================

class RAGService:
    """
    Service for RAG operations.
    
    Handles embedding generation, vector storage, and semantic search
    to provide relevant context for AI responses using PostgreSQL + pgvector.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None, chunk_config: Optional[ChunkConfig] = None):
        self.db = db
        self.chunk_config = chunk_config or ChunkConfig()
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.embedding_dimension = 1536  # text-embedding-3-small dimension
    
    # -------------------------------------------------------------------------
    # Context Retrieval
    # -------------------------------------------------------------------------
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
        filter_metadata: Optional[Dict] = None,
        include_sources: bool = False,
        namespace: Optional[str] = None
    ) -> Union[str, ContextResult]:
        """
        Retrieve relevant context from knowledge base.
        
        Args:
            query: The search query
            top_k: Maximum number of results
            score_threshold: Minimum relevance score (0-1)
            filter_metadata: Optional metadata filters
            include_sources: Whether to return detailed source info
            namespace: Optional namespace filter
        
        Returns:
            Context string or ContextResult with sources
        """
        if not self.db:
            logger.error("Database session not provided")
            return ContextResult("", [], 0, 0.0) if include_sources else ""
        
        try:
            embedding = await self._generate_embedding(query)
            
            # Build SQL query for vector similarity search
            # Using cosine distance (1 - cosine similarity)
            # Lower distance = higher similarity
            # Convert embedding list to PostgreSQL vector format string
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            
            query_sql = """
                SELECT 
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> :query_vector::vector) as similarity
                FROM vector_embeddings
                WHERE 1 - (embedding <=> :query_vector::vector) >= :threshold
            """
            
            params = {
                "query_vector": embedding_str,
                "threshold": score_threshold
            }
            
            # Add namespace filter if provided
            if namespace:
                query_sql += " AND namespace = :namespace"
                params["namespace"] = namespace
            
            # Add metadata filters if provided
            if filter_metadata:
                for key, value in filter_metadata.items():
                    # Use JSONB operators for metadata filtering
                    if isinstance(value, (dict, list)):
                        query_sql += f" AND metadata->>:key_{key} = :value_{key}::jsonb"
                        params[f"key_{key}"] = key
                        params[f"value_{key}"] = json.dumps(value)
                    else:
                        query_sql += f" AND metadata->>:key_{key} = :value_{key}"
                        params[f"key_{key}"] = key
                        params[f"value_{key}"] = str(value)
            
            query_sql += " ORDER BY similarity DESC LIMIT :top_k"
            params["top_k"] = top_k
            
            result = await self.db.execute(text(query_sql), params)
            rows = result.fetchall()
            
            # Convert to RetrievalResult objects
            matches = []
            for row in rows:
                metadata = row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata) if row.metadata else {}
                matches.append(
                    RetrievalResult(
                        content=row.content,
                        score=float(row.similarity),
                        metadata=metadata,
                        chunk_id=row.id
                    )
                )
            
            if not matches:
                logger.info(f"No results above {score_threshold} for: {query[:50]}...")
                return ContextResult("", [], 0, 0.0) if include_sources else ""
            
            # Format context
            context_parts = [self._format_context(m) for m in matches]
            context = "\n\n---\n\n".join(context_parts)
            avg_score = sum(m.score for m in matches) / len(matches)
            
            sources = [
                {
                    "title": m.metadata.get("title", "Unknown"),
                    "category": m.metadata.get("category", ""),
                    "score": round(m.score, 3),
                    "chunk_id": m.chunk_id
                }
                for m in matches
            ]
            
            if include_sources:
                return ContextResult(context, sources, len(matches), round(avg_score, 3))
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return ContextResult("", [], 0, 0.0) if include_sources else ""
    
    def _format_context(self, result: RetrievalResult) -> str:
        """Format a single context piece."""
        title = result.metadata.get("title", "")
        category = result.metadata.get("category", "")
        
        header = ""
        if title:
            header = f"**{title}**"
            if category:
                header += f" ({category})"
            header += "\n"
        
        return f"{header}{result.content}"
    
    # -------------------------------------------------------------------------
    # Embedding Generation
    # -------------------------------------------------------------------------
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        response = await get_openai_client().embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        response = await get_openai_client().embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    # -------------------------------------------------------------------------
    # Content Indexing
    # -------------------------------------------------------------------------
    
    async def index_content(
        self,
        content: str,
        metadata: Dict,
        content_id: str,
        chunk_content: bool = True,
        namespace: Optional[str] = None,
        knowledge_base_id: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Index content in PostgreSQL with pgvector.
        
        Args:
            content: The content to index
            metadata: Metadata to store with vectors
            content_id: Unique identifier for the content
            chunk_content: Whether to chunk the content
            namespace: Optional namespace
            knowledge_base_id: Optional knowledge base ID
        
        Returns:
            Tuple of (success, list of chunk IDs)
        """
        if not self.db:
            logger.error("Database session not provided")
            return False, []
        
        try:
            if chunk_content:
                return await self._index_chunked(content, metadata, content_id, namespace, knowledge_base_id)
            return await self._index_single(content, metadata, content_id, namespace, knowledge_base_id)
        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            return False, []
    
    async def _index_chunked(
        self,
        content: str,
        metadata: Dict,
        content_id: str,
        namespace: Optional[str] = None,
        knowledge_base_id: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """Index content as multiple chunks."""
        chunks = self._chunk_content(content, metadata.get("title", ""))
        
        if not chunks:
            logger.warning(f"No chunks generated for: {content_id}")
            return False, []
        
        # Generate embeddings in batch
        texts = [c["text"] for c in chunks]
        embeddings = await self._generate_embeddings_batch(texts)
        
        # Prepare and insert vectors
        chunk_ids = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{content_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Convert embedding to PostgreSQL vector format
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            
            # Prepare metadata with chunk info
            chunk_metadata = {
                **metadata,
                "content": chunk["text"],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "parent_id": content_id
            }
            
            # Insert or update vector embedding
            insert_sql = """
                INSERT INTO vector_embeddings 
                    (id, knowledge_base_id, embedding, content, metadata, namespace, chunk_index, parent_id)
                VALUES 
                    (:id, :kb_id, :embedding::vector, :content, :metadata::jsonb, :namespace, :chunk_index, :parent_id)
                ON CONFLICT (id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    namespace = EXCLUDED.namespace,
                    chunk_index = EXCLUDED.chunk_index,
                    parent_id = EXCLUDED.parent_id
            """
            
            await self.db.execute(
                text(insert_sql),
                {
                    "id": chunk_id,
                    "kb_id": knowledge_base_id,
                    "embedding": embedding_str,
                    "content": chunk["text"],
                    "metadata": json.dumps(chunk_metadata),
                    "namespace": namespace,
                    "chunk_index": i,
                    "parent_id": content_id
                }
            )
        
        await self.db.commit()
        logger.info(f"Indexed {len(chunk_ids)} chunks for: {content_id}")
        return True, chunk_ids
    
    async def _index_single(
        self,
        content: str,
        metadata: Dict,
        content_id: str,
        namespace: Optional[str] = None,
        knowledge_base_id: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """Index content as a single vector."""
        embedding = await self._generate_embedding(content)
        
        # Convert embedding to PostgreSQL vector format
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        # Prepare metadata
        full_metadata = {**metadata, "content": content}
        
        # Insert or update vector embedding
        insert_sql = """
            INSERT INTO vector_embeddings 
                (id, knowledge_base_id, embedding, content, metadata, namespace, parent_id)
            VALUES 
                (:id, :kb_id, :embedding::vector, :content, :metadata::jsonb, :namespace, :parent_id)
            ON CONFLICT (id) DO UPDATE SET
                embedding = EXCLUDED.embedding,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                namespace = EXCLUDED.namespace,
                parent_id = EXCLUDED.parent_id
        """
        
        await self.db.execute(
            text(insert_sql),
            {
                "id": content_id,
                "kb_id": knowledge_base_id,
                "embedding": embedding_str,
                "content": content,
                "metadata": json.dumps(full_metadata),
                "namespace": namespace,
                "parent_id": content_id
            }
        )
        
        await self.db.commit()
        logger.info(f"Indexed single vector: {content_id}")
        return True, [content_id]
    
    # -------------------------------------------------------------------------
    # Content Management
    # -------------------------------------------------------------------------
    
    async def delete_content(self, content_id: str, namespace: Optional[str] = None) -> bool:
        """Delete content and all its chunks from PostgreSQL."""
        if not self.db:
            logger.error("Database session not provided")
            return False
        
        try:
            # Delete chunks by parent_id
            delete_sql = "DELETE FROM vector_embeddings WHERE parent_id = :parent_id"
            params = {"parent_id": content_id}
            
            if namespace:
                delete_sql += " AND namespace = :namespace"
                params["namespace"] = namespace
            
            await self.db.execute(text(delete_sql), params)
            
            # Also delete main ID
            await self.db.execute(
                text("DELETE FROM vector_embeddings WHERE id = :id"),
                {"id": content_id}
            )
            
            await self.db.commit()
            logger.info(f"Deleted content: {content_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting content: {e}")
            await self.db.rollback()
            return False
    
    async def update_content(
        self,
        content: str,
        metadata: Dict,
        content_id: str,
        namespace: Optional[str] = None,
        knowledge_base_id: Optional[int] = None
    ) -> bool:
        """Update existing content (delete and re-index)."""
        await self.delete_content(content_id, namespace)
        success, _ = await self.index_content(
            content, metadata, content_id, 
            namespace=namespace, 
            knowledge_base_id=knowledge_base_id
        )
        return success
    
    async def search_similar(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict] = None,
        namespace: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar content without formatting."""
        if not self.db:
            return []
        
        embedding = await self._generate_embedding(query)
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        
        query_sql = """
            SELECT 
                id,
                metadata,
                1 - (embedding <=> :query_vector::vector) as similarity
            FROM vector_embeddings
            WHERE 1 - (embedding <=> :query_vector::vector) > 0
        """
        
        params = {
            "query_vector": embedding_str
        }
        
        if namespace:
            query_sql += " AND namespace = :namespace"
            params["namespace"] = namespace
        
        if filter_metadata:
            for key, value in filter_metadata.items():
                query_sql += f" AND metadata->>:key_{key} = :value_{key}"
                params[f"key_{key}"] = key
                params[f"value_{key}"] = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        
        query_sql += " ORDER BY similarity DESC LIMIT :top_k"
        params["top_k"] = top_k
        
        result = await self.db.execute(text(query_sql), params)
        rows = result.fetchall()
        
        return [
            {
                "id": row.id,
                "score": float(row.similarity),
                "metadata": row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata) if row.metadata else {}
            }
            for row in rows
        ]
    
    async def get_index_stats(self) -> Dict:
        """Get statistics about the vector embeddings."""
        if not self.db:
            return {}
        
        try:
            # Get total count
            count_result = await self.db.execute(text("SELECT COUNT(*) as count FROM vector_embeddings"))
            total_count = count_result.scalar() or 0
            
            # Get namespace counts
            ns_result = await self.db.execute(
                text("SELECT namespace, COUNT(*) as count FROM vector_embeddings GROUP BY namespace")
            )
            namespaces = {row.namespace or "default": row.count for row in ns_result.fetchall()}
            
            return {
                "total_vectors": total_count,
                "dimension": self.embedding_dimension,
                "namespaces": namespaces
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
    
    # -------------------------------------------------------------------------
    # Content Chunking
    # -------------------------------------------------------------------------
    
    def _chunk_content(self, content: str, title: str = "") -> List[Dict]:
        """Split content into chunks for embedding."""
        content = content.strip()
        if not content:
            return []
        
        # Return as single chunk if small enough
        if len(content) <= self.chunk_config.chunk_size:
            return [{"text": content, "index": 0, "total_chunks": 1}]
        
        # Split by paragraphs, then combine to target size
        raw_chunks = self._split_by_paragraphs(content)
        
        # Add title to first chunk
        chunks = []
        for i, text in enumerate(raw_chunks):
            chunk_text = text.strip()
            if i == 0 and title:
                chunk_text = f"{title}\n\n{chunk_text}"
            chunks.append({
                "text": chunk_text,
                "index": i,
                "total_chunks": len(raw_chunks)
            })
        
        return chunks
    
    def _split_by_paragraphs(self, content: str) -> List[str]:
        """Split content by paragraphs, combining small ones."""
        chunks = []
        current = ""
        
        for para in re.split(r'\n\n+', content):
            para = para.strip()
            if not para:
                continue
            
            # If paragraph is too large, split by sentences
            if len(para) > self.chunk_config.chunk_size:
                if current:
                    chunks.append(current)
                    current = ""
                
                for sentence in re.split(r'(?<=[.!?])\s+', para):
                    if len(current) + len(sentence) <= self.chunk_config.chunk_size:
                        current += (" " if current else "") + sentence
                    else:
                        if current:
                            chunks.append(current)
                        current = sentence
            else:
                # Combine paragraphs if they fit
                if len(current) + len(para) + 2 <= self.chunk_config.chunk_size:
                    current += ("\n\n" if current else "") + para
                else:
                    if current:
                        chunks.append(current)
                    current = para
        
        if current:
            chunks.append(current)
        
        return chunks
