"""Add attendance annotations table

Revision ID: c2525edcf56f
Revises: 2601fb854175
Create Date: 2026-07-23 11:54:33.012245
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c2525edcf56f'
down_revision: str | None = '2601fb854175'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('attendance_annotation',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('employee_id', sa.Integer(), nullable=False),
    sa.Column('work_date', sa.Date(), nullable=False),
    sa.Column('annotation_type', sa.String(length=64), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['employee_id'], ['employee.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('employee_id', 'work_date', name='uq_attendance_annotation_employee_date')
    )
    op.create_index(op.f('ix_attendance_annotation_annotation_type'), 'attendance_annotation', ['annotation_type'], unique=False)
    op.create_index(op.f('ix_attendance_annotation_employee_id'), 'attendance_annotation', ['employee_id'], unique=False)
    op.create_index(op.f('ix_attendance_annotation_work_date'), 'attendance_annotation', ['work_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_attendance_annotation_work_date'), table_name='attendance_annotation')
    op.drop_index(op.f('ix_attendance_annotation_employee_id'), table_name='attendance_annotation')
    op.drop_index(op.f('ix_attendance_annotation_annotation_type'), table_name='attendance_annotation')
    op.drop_table('attendance_annotation')
