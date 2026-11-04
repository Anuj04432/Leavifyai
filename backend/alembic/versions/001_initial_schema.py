"""Initial database schema migration creating core WorkforceAI tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-04 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension if available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. companies
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_companies_slug", "companies", ["slug"])

    # 2. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="employee"),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_role", "users", ["role"])

    # 3. departments
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("head_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_departments_company_id", "departments", ["company_id"])

    # 4. employees
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_code", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reporting_manager_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("date_of_joining", sa.Date(), nullable=False),
        sa.Column("date_of_exit", sa.Date(), nullable=True),
        sa.Column("employment_type", sa.String(30), nullable=False, server_default="full_time"),
        sa.Column("salary_basic", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("salary_allowances", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("bank_account_info", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("paypal_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_employees_employee_code", "employees", ["employee_code"])
    op.create_index("ix_employees_email", "employees", ["email"])
    op.create_index("ix_employees_company_id", "employees", ["company_id"])
    op.create_index("ix_employees_department_id", "employees", ["department_id"])

    # Add foreign key from departments.head_id to employees.id
    op.create_foreign_key("fk_departments_head_id", "departments", "employees", ["head_id"], ["id"], ondelete="SET NULL")

    # 5. leave_policies
    op.create_table(
        "leave_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("leave_type", sa.String(30), nullable=False),
        sa.Column("days_allowed", sa.Integer(), nullable=False),
        sa.Column("carry_forward", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_carry_forward_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requires_document", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_days_notice", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_consecutive_days", sa.Integer(), nullable=True),
        sa.Column("applicable_after_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("policy_document_ref", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_leave_policies_company_id", "leave_policies", ["company_id"])

    # 6. leave_balances
    op.create_table(
        "leave_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_allocated", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("used", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("pending", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("carried_forward", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_leave_balances_employee_id", "leave_balances", ["employee_id"])

    # 7. leave_requests
    op.create_table(
        "leave_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_number", sa.String(30), unique=True, nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_policies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("total_days", sa.Numeric(5, 1), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("source_channel", sa.String(20), nullable=False, server_default="app"),
        sa.Column("ai_recommendation", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("ai_policy_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_leave_requests_employee_id", "leave_requests", ["employee_id"])
    op.create_index("ix_leave_requests_status", "leave_requests", ["status"])

    # 8. approvals
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("leave_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_approvals_leave_request_id", "approvals", ["leave_request_id"])

    # 9. documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_employee_id", "documents", ["employee_id"])

    # 10. payroll_batches
    op.create_table(
        "payroll_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_gross", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_deductions", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("total_net", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payroll_batches_company_id", "payroll_batches", ["company_id"])

    # 11. payroll_items
    op.create_table(
        "payroll_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("basic_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_allowances", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("allowances_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("gross_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_leave_days", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("unpaid_leave_days", sa.Numeric(5, 1), nullable=False, server_default="0.0"),
        sa.Column("unpaid_leave_deduction", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("attendance_days", sa.Numeric(5, 1), nullable=True),
        sa.Column("attendance_adjustment", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("bonus", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("other_deductions", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("statutory_deductions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("total_deductions", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("net_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="calculated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payroll_items_batch_id", "payroll_items", ["batch_id"])
    op.create_index("ix_payroll_items_employee_id", "payroll_items", ["employee_id"])

    # 12. payroll_adjustments
    op.create_table(
        "payroll_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payroll_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("adjustment_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("adjusted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payroll_adjustments_payroll_item_id", "payroll_adjustments", ["payroll_item_id"])

    # 13. payments
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payroll_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payroll_items.id", ondelete="RESTRICT"), unique=True, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("payment_provider", sa.String(20), nullable=False, server_default="paypal"),
        sa.Column("provider_batch_id", sa.String(255), nullable=True),
        sa.Column("provider_item_id", sa.String(255), nullable=True),
        sa.Column("provider_transaction_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=False),
        sa.Column("recipient_identifier", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])
    op.create_index("ix_payments_status", "payments", ["status"])

    # 14. integrations
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("credentials", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="inactive"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_integrations_company_id", "integrations", ["company_id"])

    # 15. communication_events
    op.create_table(
        "communication_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("leave_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leave_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_message_id", sa.String(255), nullable=True),
        sa.Column("sender_identifier", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ai_extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_communication_events_channel", "communication_events", ["channel"])

    # 16. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("old_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("new_values", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("communication_events")
    op.drop_table("integrations")
    op.drop_table("payments")
    op.drop_table("payroll_adjustments")
    op.drop_table("payroll_items")
    op.drop_table("payroll_batches")
    op.drop_table("documents")
    op.drop_table("approvals")
    op.drop_table("leave_requests")
    op.drop_table("leave_balances")
    op.drop_table("leave_policies")
    op.drop_table("employees")
    op.drop_table("departments")
    op.drop_table("users")
    op.drop_table("companies")
