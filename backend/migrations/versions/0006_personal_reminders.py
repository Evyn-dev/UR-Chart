"""Add patient-owned arbitrary reminder tasks, separate from alerts."""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "personal_reminders",
        sa.Column("patient_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("notes", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("repeat", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_reminders_patient_id", "personal_reminders", ["patient_id"])
    op.create_index("ix_personal_reminders_patient_due", "personal_reminders", ["patient_id", "active", "due_at"])


def downgrade():
    op.drop_index("ix_personal_reminders_patient_due", table_name="personal_reminders")
    op.drop_index("ix_personal_reminders_patient_id", table_name="personal_reminders")
    op.drop_table("personal_reminders")
