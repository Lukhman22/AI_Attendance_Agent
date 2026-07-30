"""add employee salary table

Revision ID: d1e2f3g4h5i6
Revises: c4e5ac11246b
Create Date: 2026-07-29 15:56:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c4e5ac11246b'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('employee_salary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('employee_id', sa.String(length=64), nullable=False),
        sa.Column('employee_name', sa.String(length=255), nullable=True),
        sa.Column('monthly_salary', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_salary_employee_id'), 'employee_salary', ['employee_id'], unique=True)

def downgrade():
    op.drop_index(op.f('ix_employee_salary_employee_id'), table_name='employee_salary')
    op.drop_table('employee_salary')
