"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create employers table
    op.create_table(
        'employers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('ea_balance', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employers_id'), 'employers', ['id'], unique=False)

    # Create employees table
    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_code', sa.String(length=50), nullable=False),
        sa.Column('demographics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employees_id'), 'employees', ['id'], unique=False)
    op.create_index(op.f('ix_employees_employer_id'), 'employees', ['employer_id'], unique=False)
    op.create_index(op.f('ix_employees_employee_code'), 'employees', ['employee_code'], unique=False)

    # Create policy_coverages table
    op.create_table(
        'policy_coverages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insurer_id', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('plan_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_coverages_id'), 'policy_coverages', ['id'], unique=False)
    op.create_index(op.f('ix_policy_coverages_employee_id'), 'policy_coverages', ['employee_id'], unique=False)
    op.create_index(op.f('ix_policy_coverages_insurer_id'), 'policy_coverages', ['insurer_id'], unique=False)
    op.create_index(op.f('ix_policy_coverages_status'), 'policy_coverages', ['status'], unique=False)

    # Create endorsement_requests table
    op.create_table(
        'endorsement_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_endorsement_requests_id'), 'endorsement_requests', ['id'], unique=False)
    op.create_index(op.f('ix_endorsement_requests_employer_id'), 'endorsement_requests', ['employer_id'], unique=False)
    op.create_index(op.f('ix_endorsement_requests_type'), 'endorsement_requests', ['type'], unique=False)
    op.create_index(op.f('ix_endorsement_requests_status'), 'endorsement_requests', ['status'], unique=False)
    op.create_index(op.f('ix_endorsement_requests_effective_date'), 'endorsement_requests', ['effective_date'], unique=False)
    op.create_index(op.f('ix_endorsement_requests_trace_id'), 'endorsement_requests', ['trace_id'], unique=False)

    # Create ledger_transactions table
    op.create_table(
        'ledger_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('endorsement_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('external_ref', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['employer_id'], ['employers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['endorsement_id'], ['endorsement_requests.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_transactions_id'), 'ledger_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_employer_id'), 'ledger_transactions', ['employer_id'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_endorsement_id'), 'ledger_transactions', ['endorsement_id'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_type'), 'ledger_transactions', ['type'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_status'), 'ledger_transactions', ['status'], unique=False)
    op.create_index(op.f('ix_ledger_transactions_external_ref'), 'ledger_transactions', ['external_ref'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_index(op.f('ix_ledger_transactions_external_ref'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_status'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_type'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_endorsement_id'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_employer_id'), table_name='ledger_transactions')
    op.drop_index(op.f('ix_ledger_transactions_id'), table_name='ledger_transactions')
    op.drop_table('ledger_transactions')

    op.drop_index(op.f('ix_endorsement_requests_trace_id'), table_name='endorsement_requests')
    op.drop_index(op.f('ix_endorsement_requests_effective_date'), table_name='endorsement_requests')
    op.drop_index(op.f('ix_endorsement_requests_status'), table_name='endorsement_requests')
    op.drop_index(op.f('ix_endorsement_requests_type'), table_name='endorsement_requests')
    op.drop_index(op.f('ix_endorsement_requests_employer_id'), table_name='endorsement_requests')
    op.drop_index(op.f('ix_endorsement_requests_id'), table_name='endorsement_requests')
    op.drop_table('endorsement_requests')

    op.drop_index(op.f('ix_policy_coverages_status'), table_name='policy_coverages')
    op.drop_index(op.f('ix_policy_coverages_insurer_id'), table_name='policy_coverages')
    op.drop_index(op.f('ix_policy_coverages_employee_id'), table_name='policy_coverages')
    op.drop_index(op.f('ix_policy_coverages_id'), table_name='policy_coverages')
    op.drop_table('policy_coverages')

    op.drop_index(op.f('ix_employees_employee_code'), table_name='employees')
    op.drop_index(op.f('ix_employees_employer_id'), table_name='employees')
    op.drop_index(op.f('ix_employees_id'), table_name='employees')
    op.drop_table('employees')

    op.drop_index(op.f('ix_employers_id'), table_name='employers')
    op.drop_table('employers')
