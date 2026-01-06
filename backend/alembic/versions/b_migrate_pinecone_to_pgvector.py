"""Migrate from Pinecone to PostgreSQL pgvector

Revision ID: b_migrate_pinecone_to_pgvector
Revises: a7455c17a382
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b_migrate_pinecone_to_pgvector'
down_revision: Union[str, None] = 'a7455c17a382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add pgvector support."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create vector_embeddings table to store chunked embeddings
    # Note: We use text() for the vector type since SQLAlchemy doesn't have native support
    op.execute("""
        CREATE TABLE IF NOT EXISTS vector_embeddings (
            id VARCHAR PRIMARY KEY,
            knowledge_base_id INTEGER,
            embedding vector(1536) NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB,
            namespace VARCHAR,
            chunk_index INTEGER,
            parent_id VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    
    # Create indexes for vector search
    op.create_index('ix_vector_embeddings_knowledge_base_id', 'vector_embeddings', ['knowledge_base_id'], unique=False)
    op.create_index('ix_vector_embeddings_namespace', 'vector_embeddings', ['namespace'], unique=False)
    op.create_index('ix_vector_embeddings_parent_id', 'vector_embeddings', ['parent_id'], unique=False)
    
    # Create vector index for similarity search (using HNSW for performance)
    op.execute("""
        CREATE INDEX IF NOT EXISTS vector_embeddings_embedding_idx 
        ON vector_embeddings 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    
    # Update knowledge_base table - rename pinecone_id to vector_id for clarity
    # Note: We'll keep pinecone_id for now to avoid breaking existing code, but mark it as deprecated
    # The migration will add a new vector_id column
    op.add_column('knowledge_base', sa.Column('vector_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remove pgvector support."""
    # Drop vector index
    op.execute('DROP INDEX IF EXISTS vector_embeddings_embedding_idx')
    
    # Drop indexes
    op.drop_index('ix_vector_embeddings_parent_id', table_name='vector_embeddings')
    op.drop_index('ix_vector_embeddings_namespace', table_name='vector_embeddings')
    op.drop_index('ix_vector_embeddings_knowledge_base_id', table_name='vector_embeddings')
    
    # Drop vector_embeddings table
    op.execute('DROP TABLE IF EXISTS vector_embeddings')
    
    # Remove vector_id column from knowledge_base
    op.drop_column('knowledge_base', 'vector_id')
    
    # Note: We don't drop the vector extension as it might be used by other databases

