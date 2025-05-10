"""add main_photo_idx to auction

Revision ID: b1a2c3d4e5f6
Revises: a60875a027a4
Create Date: 2025-05-09 13:50:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1a2c3d4e5f6'
down_revision = 'a60875a027a4'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('main_photo_idx', sa.Integer(), nullable=True, server_default='0'))

def downgrade():
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.drop_column('main_photo_idx')
