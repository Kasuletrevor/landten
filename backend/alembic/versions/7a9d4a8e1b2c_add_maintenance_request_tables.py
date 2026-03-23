"""add maintenance request tables

Revision ID: 7a9d4a8e1b2c
Revises: f5c6c3c9c2a1
Create Date: 2026-02-12 09:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a9d4a8e1b2c"
down_revision: Union[str, None] = "f5c6c3c9c2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


maintenance_category_enum = sa.Enum(
    "plumbing",
    "electrical",
    "appliance",
    "structural",
    "other",
    name="maintenancecategory",
)
maintenance_urgency_enum = sa.Enum(
    "emergency",
    "high",
    "medium",
    "low",
    name="maintenanceurgency",
)
maintenance_status_enum = sa.Enum(
    "submitted",
    "acknowledged",
    "in_progress",
    "completed",
    "cancelled",
    name="maintenancestatus",
)
maintenance_author_enum = sa.Enum(
    "landlord",
    "tenant",
    "system",
    name="maintenanceauthortype",
)


def upgrade() -> None:
    op.create_table(
        "maintenance_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("property_id", sa.String(), nullable=False),
        sa.Column("room_id", sa.String(), nullable=False),
        sa.Column("category", maintenance_category_enum, nullable=False),
        sa.Column("urgency", maintenance_urgency_enum, nullable=False),
        sa.Column("status", maintenance_status_enum, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("preferred_entry_time", sa.String(), nullable=True),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("scheduled_visit_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("landlord_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("tenant_rating", sa.Integer(), nullable=True),
        sa.Column("tenant_feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_maintenance_requests_tenant_id")
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_maintenance_requests_property_id"),
        ),
        sa.ForeignKeyConstraint(
            ["room_id"], ["rooms.id"], name=op.f("fk_maintenance_requests_room_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_requests")),
    )
    op.create_index(
        op.f("ix_maintenance_requests_tenant_id"),
        "maintenance_requests",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_requests_property_id"),
        "maintenance_requests",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_requests_room_id"),
        "maintenance_requests",
        ["room_id"],
        unique=False,
    )

    op.create_table(
        "maintenance_comments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("author_type", maintenance_author_enum, nullable=False),
        sa.Column("author_id", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
        sa.Column("attachment_name", sa.String(), nullable=True),
        sa.Column("attachment_url", sa.String(), nullable=True),
        sa.Column("attachment_content_type", sa.String(), nullable=True),
        sa.Column("attachment_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["maintenance_requests.id"],
            name=op.f("fk_maintenance_comments_request_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_maintenance_comments")),
    )
    op.create_index(
        op.f("ix_maintenance_comments_request_id"),
        "maintenance_comments",
        ["request_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_maintenance_comments_request_id"), table_name="maintenance_comments")
    op.drop_table("maintenance_comments")

    op.drop_index(op.f("ix_maintenance_requests_room_id"), table_name="maintenance_requests")
    op.drop_index(
        op.f("ix_maintenance_requests_property_id"), table_name="maintenance_requests"
    )
    op.drop_index(
        op.f("ix_maintenance_requests_tenant_id"), table_name="maintenance_requests"
    )
    op.drop_table("maintenance_requests")

    maintenance_author_enum.drop(op.get_bind(), checkfirst=True)
    maintenance_status_enum.drop(op.get_bind(), checkfirst=True)
    maintenance_urgency_enum.drop(op.get_bind(), checkfirst=True)
    maintenance_category_enum.drop(op.get_bind(), checkfirst=True)
