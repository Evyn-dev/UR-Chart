"""Patient-visible educational curriculum, editable by any accepted demo caregiver.

Clinical instructions and medication orders are deliberately out of scope.
Every write is versioned and audit logged; revoked caregivers cannot modify tasks.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from app.auth import current_patient, get_db
from app.models import CurriculumTask, CurriculumAudit, CaregiverRelationship
from app.schemas import Data
from app.schemas.curriculum import TaskCreate, TaskEdit, TaskOut, TaskAuditOut

router = APIRouter(tags=["educational curriculum"])


def _active(db, caregiver, id):
    rel = db.scalar(select(CaregiverRelationship).where(
        CaregiverRelationship.id == str(id),
        CaregiverRelationship.caregiver_user_id == caregiver.user_id,
        CaregiverRelationship.status == "active",
    ))
    if rel is None:
        raise HTTPException(404, "Active caregiver relationship not found")
    return rel


def _items(db, patient_id):
    return db.scalars(select(CurriculumTask).where(
        CurriculumTask.patient_id == patient_id,
    ).order_by(CurriculumTask.position, CurriculumTask.created_at, CurriculumTask.id).limit(100)).all()


def _record(db, item, actor, action, before, after):
    db.add(CurriculumAudit(
        patient_id=item.patient_id, task_id=item.id,
        actor_user_id=actor.user_id, action=action, before=before, after=after,
    ))


def _snapshot(item):
    return {
        "title": item.title, "description": item.description,
        "due_day": item.due_day.isoformat() if item.due_day else None,
        "position": item.position, "status": item.status, "version": item.version,
    }


@router.get("/curriculum", response_model=Data[list[TaskOut]])
def patient_curriculum(patient=Depends(current_patient), db=Depends(get_db)):
    return {"data": _items(db, patient.id)}


@router.get("/curriculum/audit", response_model=Data[list[TaskAuditOut]])
def patient_curriculum_audit(patient=Depends(current_patient), db=Depends(get_db)):
    rows = db.scalars(select(CurriculumAudit).where(
        CurriculumAudit.patient_id == patient.id,
    ).order_by(CurriculumAudit.created_at.desc(), CurriculumAudit.id.desc()).limit(50)).all()
    return {"data": rows}


@router.get("/caregiver/relationships/{id}/curriculum", response_model=Data[list[TaskOut]])
def caregiver_curriculum(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    rel = _active(db, patient, id)
    return {"data": _items(db, rel.patient_id)}


@router.get("/caregiver/relationships/{id}/curriculum/audit", response_model=Data[list[TaskAuditOut]])
def caregiver_curriculum_audit(id: UUID, patient=Depends(current_patient), db=Depends(get_db)):
    rel = _active(db, patient, id)
    rows = db.scalars(select(CurriculumAudit).where(
        CurriculumAudit.patient_id == rel.patient_id,
    ).order_by(CurriculumAudit.created_at.desc(), CurriculumAudit.id.desc()).limit(50)).all()
    return {"data": rows}


@router.post("/caregiver/relationships/{id}/curriculum", response_model=Data[TaskOut], status_code=201)
def add_task(id: UUID, body: TaskCreate, patient=Depends(current_patient), db=Depends(get_db)):
    rel = _active(db, patient, id)
    item = CurriculumTask(patient_id=rel.patient_id, **body.model_dump())
    db.add(item)
    db.flush()
    # Serialize writes against concurrent revoke before the transaction commits.
    guard = db.execute(update(CaregiverRelationship).where(
        CaregiverRelationship.id == rel.id, CaregiverRelationship.version == rel.version,
        CaregiverRelationship.status == "active",
    ).values(updated_at=rel.updated_at))
    if guard.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Caregiver permission changed")
    _record(db, item, patient, "created", {}, _snapshot(item))
    db.commit()
    return {"data": item}


@router.patch("/caregiver/relationships/{id}/curriculum/{task_id}", response_model=Data[TaskOut])
def edit_task(id: UUID, task_id: UUID, body: TaskEdit, patient=Depends(current_patient), db=Depends(get_db)):
    rel = _active(db, patient, id)
    item = db.scalar(select(CurriculumTask).where(
        CurriculumTask.id == str(task_id), CurriculumTask.patient_id == rel.patient_id,
    ))
    if item is None:
        raise HTTPException(404, "Task not found")
    before = _snapshot(item)
    changed = body.model_dump(exclude={"expected_version"})
    guard = db.execute(update(CurriculumTask).where(
        CurriculumTask.id == item.id, CurriculumTask.patient_id == rel.patient_id,
        CurriculumTask.version == body.expected_version,
    ).values(**changed, version=body.expected_version + 1).execution_options(synchronize_session=False))
    if guard.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Task changed; reload the curriculum")
    rel_guard = db.execute(update(CaregiverRelationship).where(
        CaregiverRelationship.id == rel.id, CaregiverRelationship.version == rel.version,
        CaregiverRelationship.status == "active",
    ).values(updated_at=rel.updated_at))
    if rel_guard.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Caregiver permission changed")
    db.refresh(item)
    after = _snapshot(item)
    _record(db, item, patient, "edited" if item.status != "archived" else "archived", before, after)
    db.commit()
    return {"data": item}
