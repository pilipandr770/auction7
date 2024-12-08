"""Додано поле current_price до моделі Auction

Revision ID: 1ef04d1ecd3c
Revises: f78beaeb4a25
Create Date: 2024-12-07 15:42:18.799877

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '1ef04d1ecd3c'
down_revision = 'f78beaeb4a25'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite не підтримує зміну стовпців, тому створюємо нову таблицю з потрібними стовпцями
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=False, server_default=func.now()))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=func.now()))


def downgrade():
    # Видаляємо стовпці, якщо потрібно відкочення
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
