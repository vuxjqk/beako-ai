"""create book_chunks table

Revision ID: 5c1e7b9d2f40
Revises: a731331a8b73
Create Date: 2026-10-03 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c1e7b9d2f40'
down_revision: Union[str, None] = 'a731331a8b73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('book_chunks',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('volume_id', sa.Integer(), nullable=False),
    sa.Column('part_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('start_section_id', sa.Integer(), nullable=False),
    sa.Column('end_section_id', sa.Integer(), nullable=False),
    sa.Column('start_paragraph_id', sa.BigInteger(), nullable=False),
    sa.Column('end_paragraph_id', sa.BigInteger(), nullable=False),
    sa.Column('start_seq', sa.Integer(), nullable=False),
    sa.Column('end_seq', sa.Integer(), nullable=False),
    sa.Column('start_char', sa.Integer(), nullable=False),
    sa.Column('end_char', sa.Integer(), nullable=True),
    sa.Column('heading', sa.String(length=512), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('token_count', sa.Integer(), nullable=False),
    sa.Column('chunker_version', sa.String(length=128), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.Vector(dim=384), nullable=False),
    sa.Column('embedding_model', sa.String(length=128), nullable=False),
    sa.Column('embedding_model_version', sa.String(length=255), nullable=False),
    sa.Column('tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('simple', heading || ' ' || text)", persisted=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['volume_id'], ['volumes.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['part_id'], ['book_parts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['start_section_id'], ['book_sections.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['end_section_id'], ['book_sections.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['start_paragraph_id'], ['book_paragraphs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['end_paragraph_id'], ['book_paragraphs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('volume_id', 'ordinal')
    )
    op.create_index(op.f('ix_book_chunks_part_id'), 'book_chunks', ['part_id'], unique=False)
    op.create_index(op.f('ix_book_chunks_content_hash'), 'book_chunks', ['content_hash'], unique=False)
    op.create_index('ix_book_chunks_volume_seq', 'book_chunks', ['volume_id', 'start_seq', 'end_seq'], unique=False)
    op.create_index('ix_book_chunks_tsv', 'book_chunks', ['tsv'], unique=False, postgresql_using='gin')
    op.create_index('ix_book_chunks_embedding_hnsw', 'book_chunks', ['embedding'], unique=False,
                    postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})


def downgrade() -> None:
    op.drop_index('ix_book_chunks_embedding_hnsw', table_name='book_chunks')
    op.drop_index('ix_book_chunks_tsv', table_name='book_chunks')
    op.drop_index('ix_book_chunks_volume_seq', table_name='book_chunks')
    op.drop_index(op.f('ix_book_chunks_content_hash'), table_name='book_chunks')
    op.drop_index(op.f('ix_book_chunks_part_id'), table_name='book_chunks')
    op.drop_table('book_chunks')
