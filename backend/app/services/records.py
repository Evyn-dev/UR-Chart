from fastapi import HTTPException
from sqlalchemy import select


def owned(db, model, record_id, patient_id):
    record = db.scalar(select(model).where(model.id == str(record_id), model.patient_id == patient_id))
    if record is None:
        raise HTTPException(404, "Record not found")
    return record


def listing(db, model, patient_id, limit, offset):
    return db.scalars(select(model).where(model.patient_id == patient_id).order_by(model.created_at.desc(), model.id).offset(offset).limit(limit)).all()


def save(db, record):
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
