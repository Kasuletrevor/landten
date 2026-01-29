"""add_grace_period_and_primary_currency

Revision ID: bfae22a1f527
Revises: 9f9f3f7f8cf9
Create Date: 2026-01-30 00:57:04.749307

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bfae22a1f527"
down_revision: Union[str, None] = "9f9f3f7f8cf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add primary_currency to landlords with default 'UGX'
    with op.batch_alter_table("landlords", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "primary_currency", sa.String(), nullable=False, server_default="UGX"
            )
        )

    # Add grace_period_days to properties with default 5
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "grace_period_days", sa.Integer(), nullable=False, server_default="5"
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("properties", schema=None) as batch_op:
        batch_op.drop_column("grace_period_days")

    with op.batch_alter_table("landlords", schema=None) as batch_op:
        batch_op.drop_column("primary_currency")
