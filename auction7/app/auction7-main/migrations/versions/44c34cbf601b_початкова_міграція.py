"""Початкова міграція

Revision ID: 44c34cbf601b
Revises: 
Create Date: 2024-12-11 21:05:28.960468

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '44c34cbf601b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('balance', sa.Float(), nullable=True),
    sa.Column('platform_balance', sa.Float(), nullable=True),
    sa.Column('user_type', sa.String(length=10), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('auctions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('starting_price', sa.Float(), nullable=False),
    sa.Column('current_price', sa.Float(), nullable=False),
    sa.Column('seller_id', sa.Integer(), nullable=False),
    sa.Column('total_participants', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('winner_id', sa.Integer(), nullable=True),
    sa.Column('total_earnings', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('photos', sqlite.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['winner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('auction_participants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('auction_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('has_paid_entry', sa.Boolean(), nullable=False),
    sa.Column('has_viewed_price', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['auction_id'], ['auctions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('auction_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('purpose', sa.String(length=50), nullable=False),
    sa.Column('recipient', sa.String(length=50), nullable=False),
    sa.Column('is_processed', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['auction_id'], ['auctions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('payments')
    op.drop_table('auction_participants')
    op.drop_table('auctions')
    op.drop_table('users')
    # ### end Alembic commands ###
