"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Helpers — every operation is fully idempotent so partial runs from
    # previous attempts never block a retry.
    # ------------------------------------------------------------------

    def _make_enum(type_name: str, values: list[str]) -> None:
        """Create a PG enum type, silently skip if it already exists."""
        quoted = ", ".join(f"'{v}'" for v in values)
        # DO block + EXCEPTION is the only 100%-reliable idempotent approach
        # for enum types in PostgreSQL.  Works correctly with psycopg2 because
        # dollar-quoted blocks are handled by libpq directly.
        conn.execute(
            sa.text(
                f"DO $ENUM$ BEGIN "
                f"  CREATE TYPE {type_name} AS ENUM ({quoted}); "
                f"EXCEPTION WHEN duplicate_object THEN NULL; "
                f"END $ENUM$;"
            )
        )

    def _table_exists(name: str) -> bool:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :n"
                ),
                {"n": name},
            ).scalar()
        )

    def _index_exists(name: str) -> bool:
        return bool(
            conn.execute(
                sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
                {"n": name},
            ).scalar()
        )

    def _create_index(
        index_name: str, table: str, columns: list[str], unique: bool = False
    ) -> None:
        if not _index_exists(index_name):
            unique_kw = "UNIQUE " if unique else ""
            cols = ", ".join(columns)
            conn.execute(sa.text(f"CREATE {unique_kw}INDEX {index_name} ON {table} ({cols})"))

    # ------------------------------------------------------------------
    # ENUM types
    # ------------------------------------------------------------------
    _make_enum(
        "da_status_enum",
        [
            "UPLOADING",
            "AI_PROCESSING",
            "PENDING_ACCOUNTANT_REVIEW",
            "PENDING_OPERATOR_APPROVAL",
            "APPROVED",
            "REJECTED",
            "PUSHED_TO_ERP",
        ],
    )
    _make_enum("cost_item_source_enum", ["PDA", "FDA"])
    _make_enum(
        "category_enum",
        [
            "PILOTAGE",
            "TOWAGE",
            "PORT_DUES",
            "AGENCY_FEE",
            "LAUNCH_HIRE",
            "WASTE_DISPOSAL",
            "OTHER",
        ],
    )
    _make_enum(
        "doc_type_enum",
        [
            "DIGITAL_INVOICE",
            "SCANNED_RECEIPT",
            "HANDWRITTEN_CHIT",
            "OFFICIAL_RECEIPT",
        ],
    )
    _make_enum(
        "item_status_enum",
        [
            "OK",
            "REQUIRES_REVIEW",
            "CONFIRMED",
            "OVERRIDDEN",
        ],
    )
    _make_enum(
        "flag_reason_enum",
        [
            "LOW_CONFIDENCE",
            "MISSING_PDA_LINE",
            "HIGH_DEVIATION",
            "MISSING_FROM_FDA",
        ],
    )

    # ------------------------------------------------------------------
    # Tables
    # Use postgresql.ENUM(name=..., create_type=False) for enum columns —
    # unlike sa.Enum(), this dialect-specific type does NOT register an
    # _on_table_create listener, so it never tries to re-emit CREATE TYPE.
    # ------------------------------------------------------------------

    if not _table_exists("port_calls"):
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
    _create_index("ix_port_calls_port_call_id", "port_calls", ["port_call_id"], unique=True)
    _create_index("ix_port_calls_vessel_imo", "port_calls", ["vessel_imo"])
    _create_index("ix_port_calls_port_code", "port_calls", ["port_code"])

    if not _table_exists("disbursement_accounts"):
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
                PgEnum(name="da_status_enum", create_type=False),
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
    _create_index(
        "ix_disbursement_accounts_port_call_fk", "disbursement_accounts", ["port_call_fk"]
    )
    _create_index("ix_disbursement_accounts_status", "disbursement_accounts", ["status"])
    _create_index(
        "ix_disbursement_accounts_celery_job_id", "disbursement_accounts", ["celery_job_id"]
    )

    if not _table_exists("cost_items"):
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
                "source", PgEnum(name="cost_item_source_enum", create_type=False), nullable=False
            ),
            sa.Column("category", PgEnum(name="category_enum", create_type=False), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("estimated_value", sa.Float(), nullable=True),
            sa.Column("actual_value", sa.Float(), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
            sa.Column("confidence_score", sa.Float(), nullable=True),
            sa.Column(
                "supporting_document_type",
                PgEnum(name="doc_type_enum", create_type=False),
                nullable=True,
            ),
            sa.Column("bounding_box", postgresql.JSONB(), nullable=True),
            sa.Column("abs_variance", sa.Float(), nullable=True),
            sa.Column("pct_variance", sa.Float(), nullable=True),
            sa.Column(
                "review_status",
                PgEnum(name="item_status_enum", create_type=False),
                nullable=False,
                server_default="OK",
            ),
            sa.Column(
                "flag_reason", PgEnum(name="flag_reason_enum", create_type=False), nullable=True
            ),
            sa.Column("flag_reasons", postgresql.JSONB(), nullable=True),
            sa.Column("accountant_note", sa.Text(), nullable=True),
            sa.Column("operator_justification", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        )
    _create_index("ix_cost_items_da_fk", "cost_items", ["da_fk"])
    _create_index("ix_cost_items_category", "cost_items", ["category"])
    _create_index("ix_cost_items_review_status", "cost_items", ["review_status"])

    if not _table_exists("audit_log"):
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
    _create_index("ix_audit_log_da_fk", "audit_log", ["da_fk"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("cost_items")
    op.drop_table("disbursement_accounts")
    op.drop_table("port_calls")

    for name in [
        "flag_reason_enum",
        "item_status_enum",
        "doc_type_enum",
        "category_enum",
        "cost_item_source_enum",
        "da_status_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
