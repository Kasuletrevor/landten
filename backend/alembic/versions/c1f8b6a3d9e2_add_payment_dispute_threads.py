"""add payment dispute threads

Revision ID: c1f8b6a3d9e2
Revises: b8164dad9fc4
Create Date: 2026-02-09 19:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1f8b6a3d9e2"
down_revision: Union[str, None] = "b8164dad9fc4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


dispute_status_enum = sa.Enum("open", "resolved", name="disputestatus")
dispute_actor_enum = sa.Enum("landlord", "tenant", "system", name="disputeactortype")
notification_enum_old = sa.Enum(
    "PAYMENT_DUE",
    "PAYMENT_OVERDUE",
    "PAYMENT_RECEIVED",
    "TENANT_ADDED",
    "TENANT_REMOVED",
    "REMINDER_SENT",
    name="notificationtype",
)
notification_enum_new = sa.Enum(
    "PAYMENT_DUE",
    "PAYMENT_OVERDUE",
    "PAYMENT_RECEIVED",
    "TENANT_ADDED",
    "TENANT_REMOVED",
    "REMINDER_SENT",
    "PAYMENT_DISPUTE_MESSAGE",
    name="notificationtype",
)


def upgrade() -> None:
    op.create_table(
        "payment_disputes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("payment_id", sa.String(), nullable=False),
        sa.Column("status", dispute_status_enum, nullable=False),
        sa.Column("opened_by_type", dispute_actor_enum, nullable=False),
        sa.Column("opened_by_id", sa.String(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_by_type", dispute_actor_enum, nullable=True),
        sa.Column("resolved_by_id", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("landlord_last_read_at", sa.DateTime(), nullable=True),
        sa.Column("tenant_last_read_at", sa.DateTime(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["payment_id"], ["payments.id"], name=op.f("fk_payment_disputes_payment_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_disputes")),
    )
    op.create_index(
        op.f("ix_payment_disputes_payment_id"),
        "payment_disputes",
        ["payment_id"],
        unique=True,
    )

    op.create_table(
        "payment_dispute_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("dispute_id", sa.String(), nullable=False),
        sa.Column("payment_id", sa.String(), nullable=False),
        sa.Column("author_type", dispute_actor_enum, nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dispute_id"],
            ["payment_disputes.id"],
            name=op.f("fk_payment_dispute_messages_dispute_id"),
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_payment_dispute_messages_payment_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_dispute_messages")),
    )
    op.create_index(
        op.f("ix_payment_dispute_messages_dispute_id"),
        "payment_dispute_messages",
        ["dispute_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_dispute_messages_payment_id"),
        "payment_dispute_messages",
        ["payment_id"],
        unique=False,
    )

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=notification_enum_old,
            type_=notification_enum_new,
            existing_nullable=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_payment_dispute_messages_payment_id"),
        table_name="payment_dispute_messages",
    )
    op.drop_index(
        op.f("ix_payment_dispute_messages_dispute_id"),
        table_name="payment_dispute_messages",
    )
    op.drop_table("payment_dispute_messages")

    op.drop_index(op.f("ix_payment_disputes_payment_id"), table_name="payment_disputes")
    op.drop_table("payment_disputes")

    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=notification_enum_new,
            type_=notification_enum_old,
            existing_nullable=False,
        )

    dispute_actor_enum.drop(op.get_bind(), checkfirst=True)
    dispute_status_enum.drop(op.get_bind(), checkfirst=True)
