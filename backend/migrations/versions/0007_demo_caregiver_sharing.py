"""Grant the fictional demo caregiver access to the fictional demo patient only.

Data-only migration for existing test/demo databases. No real patient identities
are matched. The migration is safe on an empty database and leaves real records
untouched. Downgrade deliberately does not revoke consent or remove audit logs.
"""
from uuid import uuid4
from datetime import datetime, timezone
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SCOPES = ["recovery_summary", "checkin_summary", "medication_adherence", "alerts"]
SEVERITIES = ["routine", "needs_clinical_review", "urgent", "emergency"]


def upgrade():
    connection = op.get_bind()
    patient = connection.execute(
        sa.text("SELECT id FROM patients WHERE user_id = :identity"),
        {"identity": "synthetic-demo-patient"},
    ).scalar_one_or_none()
    if not patient:
        return

    meta = sa.MetaData()
    rels = sa.Table("caregiver_relationships", meta, autoload_with=connection)
    audits = sa.Table("caregiver_audits", meta, autoload_with=connection)
    existing = connection.execute(
        sa.select(rels).where(
            rels.c.patient_id == patient,
            rels.c.caregiver_user_id == "synthetic-demo-caregiver",
        )
    ).mappings().first()
    now = datetime.now(timezone.utc)
    if existing is None:
        relation_id = str(uuid4())
        connection.execute(sa.insert(rels).values(
            id=relation_id, patient_id=patient,
            caregiver_user_id="synthetic-demo-caregiver", status="active",
            permissions=SCOPES, alert_severities=SEVERITIES, version=1,
            responded_at=now, revoked_at=None, created_at=now, updated_at=now,
        ))
        for actor, action in [
            ("synthetic-demo-patient", "invitation_created"),
            ("synthetic-demo-caregiver", "invitation_accepted"),
        ]:
            connection.execute(sa.insert(audits).values(
                id=str(uuid4()), patient_id=patient, relationship_id=relation_id,
                actor_user_id=actor, action=action,
                details={"source": "fictional_demo_migration", "permissions": SCOPES},
                created_at=now, updated_at=now,
            ))
    else:
        old = dict(existing)
        if (old["status"] == "active" and
            set(old["permissions"]) == set(SCOPES) and
            set(old["alert_severities"]) == set(SEVERITIES)):
            return
        connection.execute(
            sa.update(rels).where(rels.c.id == old["id"]).values(
                status="active", permissions=SCOPES, alert_severities=SEVERITIES,
                responded_at=old["responded_at"] or now, revoked_at=None,
                version=old["version"] + 1, updated_at=now,
            )
        )
        connection.execute(sa.insert(audits).values(
            id=str(uuid4()), patient_id=patient, relationship_id=old["id"],
            actor_user_id="synthetic-demo-patient", action="demo_access_restored",
            details={"source": "fictional_demo_migration",
                     "before": {"status": old["status"], "permissions": old["permissions"],
                                "alert_severities": old["alert_severities"]},
                     "after": {"status": "active", "permissions": SCOPES,
                               "alert_severities": SEVERITIES}},
            created_at=now, updated_at=now,
        ))


def downgrade():
    # Preserves historical audit logs and user-modified relationships.
    pass
