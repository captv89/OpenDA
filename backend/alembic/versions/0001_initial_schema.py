"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # ENUM types — must be created before the tables that use them
    # -----------------------------------------------------------------
    da_status_enum = postgresql.ENUM(
        "UPLOADING",
        "AI_PROCESSING",
        "PENDING_ACCOUNTANT_REVIEW",
        "PENDING_OPERATOR_APPROVAL",
        "APPROVED",
        "REJECTED",
        "PUSHED_TO_ERP",
        name="da_status_enum",
    )
    da_status_enum.create(op.get_bind())

    cost_item_source_enum = postgresql.ENUM(
        "PDA", "FDA", name="cost_item_source_enum"
    )
    cost_item_source_enum.create(op.get_bind())

    category_enum = postgresql.ENUM(
        "PILOTAGE",
        "TOWAGE",
        "PORT_DUES",
        "AGENCY_FEE",
        "LAUNCH_HIRE",
        "WASTE_DISPOSAL",
        "OTHER",
        name="category_enum",
    )
    category_enum.create(op.get_bind())

    doc_type_enum = postgresql.ENUM(
        "DIGITAL_INVOICE",
        "SCANNED_RECEIPT",
        "HANDWRITTEN_CHIT",
        "OFFICIAL_RECEIPT",
        name="doc_type_enum",
    )
    doc_type_enum.create(op.get_bind())

    item_status_enum = postgresql.ENUM(
        "OK", "REQUIRES_REVIEW", "CONFIRMED", "OVERRIDDEN", name="item_status_enum"
    )
    item_status_enum.create(op.get_bind())

    flag_reason_enum = postgresql.ENUM(
        "LOW_CONFIDENCE",
        "MISSING_PDA_LINE",
        "HIGH_DEVIATION",
        "MISSING_FROM_FDA",
        name="flag_reason_enum",
    )
    flag_reason_enum.create(op.get_bind())

    # -----------------------------------------------------------------
    # port_calls
    # -----------------------------------------------------------------
    op.create_table(
        "port_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("port_call_id", sa.String(50), nullable=False),
        sa.Column("vessel_name", sa.String(200), nullable=False),
        sa.Column("vessel_imo", sa.String(7), nullable=False),
        sa.Column("port_code", sa.String(5), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_port_calls_port_call_id", "port_calls", ["port_call_id"], unique=True)
    op.create_index("ix_port_calls_vessel_imo", "port_calls", ["vessel_imo"])
    op.create_index("ix_port_calls_port_code", "port_calls", ["port_code"])

    # -----------------------------------------------------------------
    # disbursement_accounts
    # -----------------------------------------------------------------
    op.create_table(
        "disbursement_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "port_call_fk",
            sa.String(36),
            sa.ForeignKey("port_calls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "UPLOADING",
                "AI_PROCESSING",
                "PENDING_ACCOUNTANT_REVIEW",
                "PENDING_OPERATOR_APPROVAL",
                "APPROVED",
                "REJECTED",
                "PUSHED_TO_ERP",
                name="da_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="UPLOADING",
        ),
        sa.Column("pdf_path", sa.Text(), nullable=True),
        sa.Column("celery_job_id", sa.String(155), nullable=True),
        sa.Column("extraction_model", sa.String(100), nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("pda_json", postgresql.JSONB(), nullable=True),
        sa.Column("fda_json", postgresql.JSONB(), nullable=True),
        sa.Column("deviation_report", postgresql.JSONB(), nullable=True),
        sa.Column("accountant_user_id", sa.String(100), nullable=True),
        sa.Column("operator_user_id", sa.String(100), nullable=True),
        sa.Column("operator_remarks", sa.Text(), nullable=True),
        sa.Column("flagged_items_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_estimated", sa.Float(), nullable=True),
        sa.Column("total_actual", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_disbursement_accounts_port_call_fk", "disbursement_accounts", ["port_call_fk"])
    op.create_index("ix_disbursement_accounts_status", "disbursement_accounts", ["status"])
    op.create_index("ix_disbursement_accounts_celery_job_id", "disbursement_accounts", ["celery_job_id"])

    # -----------------------------------------------------------------
    # cost_items
    # -----------------------------------------------------------------
    op.create_table(
        "cost_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "da_fk",
            sa.String(36),
            sa.ForeignKey("disbursement_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.Enum("PDA", "FDA", name="cost_item_source_enum", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "PILOTAGE", "TOWAGE", "PORT_DUES", "AGENCY_FEE",
                "LAUNCH_HIRE", "WASTE_DISPOSAL", "OTHER",
                name="category_enum", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "supporting_document_type",
            sa.Enum(
                "DIGITAL_INVOICE", "SCANNED_RECEIPT", "HANDWRITTEN_CHIT", "OFFICIAL_RECEIPT",
                name="doc_type_enum", create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("bounding_box", postgresql.JSONB(), nullable=True),
        sa.Column("abs_variance", sa.Float(), nullable=True),
        sa.Column("pct_variance", sa.Float(), nullable=True),
        sa.Column(
            "review_status",
            sa.Enum(
                "OK", "REQUIRES_REVIEW", "CONFIRMED", "OVERRIDDEN",
                name="item_status_enum", create_type=False,
            ),
            nullable=False,
            server_default="OK",
        ),
        sa.Column(
            "flag_reason",
            sa.Enum(
                "LOW_CONFIDENCE", "MISSING_PDA_LINE", "HIGH_DEVIATION", "MISSING_FROM_FDA",
                name="flag_reason_enum", create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("flag_reasons", postgresql.JSONB(), nullable=True),
        sa.Column("accountant_note", sa.Text(), nullable=True),
        sa.Column("operator_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_cost_items_da_fk", "cost_items", ["da_fk"])
    op.create_index("ix_cost_items_category", "cost_items", ["category"])
    op.create_index("ix_cost_items_review_status", "cost_items", ["review_status"])

    # -----------------------------------------------------------------
    # audit_log
    # -----------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "da_fk",
            sa.String(36),
            sa.ForeignKey("disbursement_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_audit_log_da_fk", "audit_log", ["da_fk"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("cost_items")
    op.drop_table("disbursement_accounts")
    op.drop_table("port_calls")

    # Drop enums in reverse dependency order
    for name in [
        "flag_reason_enum",
        "item_status_enum",
        "doc_type_enum",
        "category_enum",
        "cost_item_source_enum",
        "da_status_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
