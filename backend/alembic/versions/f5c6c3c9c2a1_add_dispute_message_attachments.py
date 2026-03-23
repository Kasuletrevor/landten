"""add dispute message attachment fields

Revision ID: f5c6c3c9c2a1
Revises: 18bf506932ee
Create Date: 2026-02-10 10:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f5c6c3c9c2a1"
down_revision: Union[str, None] = "18bf506932ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("payment_dispute_messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("attachment_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("attachment_url", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("attachment_content_type", sa.String(), nullable=True)
        )
        batch_op.add_column(sa.Column("attachment_size_bytes", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payment_dispute_messages", schema=None) as batch_op:
        batch_op.drop_column("attachment_size_bytes")
        batch_op.drop_column("attachment_content_type")
        batch_op.drop_column("attachment_url")
        batch_op.drop_column("attachment_name")
