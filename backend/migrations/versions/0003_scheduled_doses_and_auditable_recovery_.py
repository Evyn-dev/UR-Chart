"""Scheduled doses and auditable recovery safety"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('checkins', schema=None) as batch_op:
        batch_op.add_column(sa.Column('symptom_reports', sa.JSON(), nullable=False, server_default='[]'))
        batch_op.add_column(sa.Column('activity_type', sa.String(length=100), nullable=True))
        batch_op.alter_column('wellbeing',
               existing_type=sa.INTEGER(),
               nullable=True)

    op.create_table('medication_schedules',
    sa.Column('medication_id', sa.String(length=36), nullable=False),
    sa.Column('timezone', sa.String(length=100), nullable=False),
    sa.Column('reminder_times', sa.JSON(), nullable=False),
    sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
    sa.Column('effective_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['medication_id'], ['medications.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('medication_schedules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_medication_schedules_medication_id'), ['medication_id'], unique=False)

    op.create_table('risk_evaluations',
    sa.Column('checkin_id', sa.String(length=36), nullable=False),
    sa.Column('ruleset_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('details', sa.JSON(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['checkin_id'], ['checkins.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('checkin_id', 'ruleset_hash', name='uq_checkin_ruleset')
    )
    with op.batch_alter_table('risk_evaluations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_risk_evaluations_checkin_id'), ['checkin_id'], unique=False)

    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('severity', sa.String(length=30), nullable=False, server_default='routine'))
        batch_op.add_column(sa.Column('checkin_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('rule_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('rule_version', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('prototype_only', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('evidence', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('notification_status', sa.String(length=30), nullable=False, server_default='not_sent'))
        batch_op.create_index(batch_op.f('ix_alerts_checkin_id'), ['checkin_id'], unique=False)
        batch_op.create_unique_constraint('uq_alert_checkin_rule', ['checkin_id', 'rule_id', 'rule_version'])
        batch_op.create_foreign_key('fk_alert_checkin', 'checkins', ['checkin_id'], ['id'])

    with op.batch_alter_table('medication_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('schedule_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('units_used', sa.Integer(), nullable=True))
        batch_op.create_unique_constraint('uq_medication_scheduled_dose', ['medication_id', 'scheduled_for'])
        batch_op.create_foreign_key('fk_log_schedule', 'medication_schedules', ['schedule_id'], ['id'])

    from datetime import datetime, timezone
    from uuid import uuid4
    connection = op.get_bind()
    medications = sa.table('medications', sa.column('id', sa.String), sa.column('patient_id', sa.String), sa.column('active', sa.Boolean), sa.column('reminder_times', sa.JSON))
    patients = sa.table('patients', sa.column('id', sa.String), sa.column('timezone', sa.String))
    schedules = sa.table('medication_schedules', sa.column('id', sa.String), sa.column('medication_id', sa.String), sa.column('timezone', sa.String), sa.column('reminder_times', sa.JSON), sa.column('effective_from', sa.DateTime(timezone=True)), sa.column('created_at', sa.DateTime(timezone=True)), sa.column('updated_at', sa.DateTime(timezone=True)))
    at = datetime.now(timezone.utc)
    for row in connection.execute(sa.select(medications.c.id, medications.c.reminder_times, patients.c.timezone).join(patients, patients.c.id == medications.c.patient_id).where(medications.c.active.is_(True))):
        if row.reminder_times:
            connection.execute(schedules.insert().values(id=str(uuid4()), medication_id=row.id, timezone=row.timezone, reminder_times=row.reminder_times, effective_from=at, created_at=at, updated_at=at))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM checkins WHERE wellbeing IS NULL")).scalar():
        raise RuntimeError("Cannot downgrade partial check-ins without losing information; export and reconcile first")
    with op.batch_alter_table('medication_logs', schema=None) as batch_op:
        batch_op.drop_constraint('fk_log_schedule', type_='foreignkey')
        batch_op.drop_constraint('uq_medication_scheduled_dose', type_='unique')
        batch_op.drop_column('units_used')
        batch_op.drop_column('scheduled_for')
        batch_op.drop_column('schedule_id')

    with op.batch_alter_table('alerts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_alert_checkin', type_='foreignkey')
        batch_op.drop_constraint('uq_alert_checkin_rule', type_='unique')
        batch_op.drop_index(batch_op.f('ix_alerts_checkin_id'))
        batch_op.drop_column('notification_status')
        batch_op.drop_column('evidence')
        batch_op.drop_column('prototype_only')
        batch_op.drop_column('rule_version')
        batch_op.drop_column('rule_id')
        batch_op.drop_column('checkin_id')
        batch_op.drop_column('severity')

    with op.batch_alter_table('risk_evaluations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_risk_evaluations_checkin_id'))

    op.drop_table('risk_evaluations')
    with op.batch_alter_table('checkins', schema=None) as batch_op:
        batch_op.alter_column('wellbeing',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_column('activity_type')
        batch_op.drop_column('symptom_reports')

    with op.batch_alter_table('medication_schedules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_medication_schedules_medication_id'))

    op.drop_table('medication_schedules')
