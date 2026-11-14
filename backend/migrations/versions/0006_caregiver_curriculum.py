"""Caregiver-managed educational recovery tasks and immutable change history."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "curriculum_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("due_day", sa.Date(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_curriculum_tasks_patient_id", "curriculum_tasks", ["patient_id"])
    op.create_index("ix_curriculum_patient_order", "curriculum_tasks", ["patient_id", "position", "created_at"])
    op.create_table(
        "curriculum_audits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("curriculum_tasks.id"), nullable=False),
        sa.Column("actor_user_id", sa.String(255), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_curriculum_audits_patient_id", "curriculum_audits", ["patient_id"])
    op.create_index("ix_curriculum_audit_task_time", "curriculum_audits", ["patient_id", "task_id", "created_at"])

def downgrade():
    op.drop_index("ix_curriculum_audit_task_time", table_name="curriculum_audits")
    op.drop_index("ix_curriculum_audits_patient_id", table_name="curriculum_audits")
    op.drop_table("curriculum_audits")
    op.drop_index("ix_curriculum_patient_order", table_name="curriculum_tasks")
    op.drop_index("ix_curriculum_tasks_patient_id", table_name="curriculum_tasks")
    op.drop_table("curriculum_tasks")
