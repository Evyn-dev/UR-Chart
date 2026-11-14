"""Add recovery tracking fields for medications and check-ins.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("medications") as batch:
        batch.add_column(sa.Column("reminder_times", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("supply_remaining", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("refill_threshold", sa.Integer(), nullable=True))
    with op.batch_alter_table("checkins") as batch:
        batch.add_column(sa.Column("pain_level", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("symptoms", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("activity_minutes", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("checkins") as batch:
        batch.drop_column("activity_minutes")
        batch.drop_column("symptoms")
        batch.drop_column("pain_level")
    with op.batch_alter_table("medications") as batch:
        batch.drop_column("refill_threshold")
        batch.drop_column("supply_remaining")
        batch.drop_column("reminder_times")
