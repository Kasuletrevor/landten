"""add_currency_to_rooms

Revision ID: 9f9f3f7f8cf9
Revises: a95e846d7956
Create Date: 2025-12-31 23:12:13.042873

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f9f3f7f8cf9"
down_revision: Union[str, None] = "a95e846d7956"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add currency column with default value for existing rows
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("currency", sa.String(), nullable=False, server_default="UGX")
        )


def downgrade() -> None:
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.drop_column("currency")
