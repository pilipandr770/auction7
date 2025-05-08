"""add is_confirmed to auction

Revision ID: a60875a027a4
Revises: 01245ad1bf17
Create Date: 2025-05-08 17:55:01.564620

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a60875a027a4'
down_revision = '01245ad1bf17'
branch_labels = None
depends_on = None


def upgrade():
    # Додаємо лише колонку is_confirmed, не створюємо таблицю seller_verifications
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('auctions', schema=None) as batch_op:
        batch_op.drop_column('is_confirmed')
