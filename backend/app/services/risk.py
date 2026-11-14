"""Deterministic, auditable rule matching. No diagnosis or LLM decision-making."""
import hashlib
import json
from pathlib import Path
from typing import Literal
from datetime import timedelta
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models import Alert, Checkin, RiskEvaluation

EMERGENCY_GUIDANCE = "For a possible immediate emergency, contact emergency services now (911 in the United States; your local emergency number elsewhere). Do not wait for this app or a reply from your care team."
FALLBACK_GUIDANCE = "This check-in has not been clinically assessed. Contact your care team about concerning or worsening symptoms. " + EMERGENCY_GUIDANCE


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    prototype_only: bool = True
    reviewed_by: str | None = None
    review_reference: str | None = None
    kind: Literal["symptom", "increase"]
    symptom_code: str | None = None
    field: Literal["pain_level", "wellbeing", "activity_minutes"] | None = None
    minimum_increase: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    lookback_days: int | None = Field(default=None, ge=1, le=30)
    severity: Literal["routine", "needs_clinical_review", "urgent", "emergency"]
    guidance: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def complete(self):
        if not self.prototype_only and not (self.reviewed_by and self.review_reference):
            raise ValueError("Clinical rules require reviewer and reference")
        if self.kind == "symptom" and not self.symptom_code:
            raise ValueError("Symptom rule requires code")
        if self.kind == "increase" and (not self.field or self.minimum_increase is None or self.lookback_days is None or self.prototype_only):
            raise ValueError("Trend rules require explicit reviewed parameters; no prototype clinical thresholds")
        return self


class Ruleset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[Rule] = Field(max_length=100)

    @model_validator(mode="after")
    def unique(self):
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("Duplicate rule IDs")
        return self


def load_rules(settings):
    path = Path(settings.risk_rules_file) if settings.risk_rules_file else Path(__file__).parents[1] / "risk_rules.demo.json"
    ruleset = Ruleset.model_validate_json(path.read_text(encoding="utf-8"))
    if settings.app_env == "production" and any(r.prototype_only for r in ruleset.rules):
        raise ValueError("Prototype rules cannot run in production")
    return ruleset


def match(db, checkin, rule):
    if rule.kind == "symptom":
        for report in checkin.symptom_reports:
            if report["code"] == rule.symptom_code and report["present"]:
                return {"symptom": report}
        return None
    value = getattr(checkin, rule.field)
    if value is None:
        return None
    previous = db.scalar(select(Checkin).where(Checkin.patient_id == checkin.patient_id,
        Checkin.day < checkin.day, Checkin.day >= checkin.day - timedelta(days=rule.lookback_days),
        getattr(Checkin, rule.field).is_not(None)).order_by(Checkin.day.desc()).limit(1))
    if previous is not None:
        baseline = getattr(previous, rule.field)
        if value - baseline >= rule.minimum_increase:
            return {"field": rule.field, "value": value, "previous_value": baseline, "previous_checkin_id": previous.id, "increase": value - baseline}
    return None


def persist_alert(db, checkin, rule_id, version, severity, guidance, evidence, prototype=True):
    existing = db.scalar(select(Alert).where(Alert.checkin_id == checkin.id, Alert.rule_id == rule_id, Alert.rule_version == version, Alert.checkin_version == checkin.version))
    if existing:
        return existing
    alert = Alert(patient_id=checkin.patient_id, checkin_id=checkin.id, category="recovery_safety",
        rule_id=rule_id, rule_version=version, checkin_version=checkin.version, severity=severity, prototype_only=prototype,
        message=("PROTOTYPE ONLY — not clinically validated. " if prototype else "") + guidance,
        evidence=evidence, notification_status="not_sent")
    try:
        with db.begin_nested():
            db.add(alert)
            db.flush()
    except IntegrityError:
        return db.scalar(select(Alert).where(Alert.checkin_id == checkin.id, Alert.rule_id == rule_id, Alert.rule_version == version, Alert.checkin_version == checkin.version))
    return alert


def evaluate(db, checkin, settings):
    try:
        ruleset = load_rules(settings)
        snapshot = ruleset.model_dump(mode="json")
        fingerprint = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    except (OSError, ValueError):
        ruleset, snapshot, fingerprint = None, {}, "unavailable"
    existing = db.scalar(select(RiskEvaluation).where(RiskEvaluation.checkin_id == checkin.id, RiskEvaluation.ruleset_hash == fingerprint, RiskEvaluation.checkin_version == checkin.version))
    if existing:
        return existing
    details = {"checkin_version": checkin.version, "ruleset": snapshot, "matched_rules": [], "guidance": FALLBACK_GUIDANCE, "prototype_only": True}
    status = "unavailable" if ruleset is None else "evaluated"
    if ruleset is None or not ruleset.rules:
        status = "unavailable"
        persist_alert(db, checkin, "assessment_unavailable", "1", "needs_clinical_review", FALLBACK_GUIDANCE, {"reason": "No usable safety rules"})
    else:
        details["prototype_only"] = any(rule.prototype_only for rule in ruleset.rules)
        status = "prototype_evaluated" if details["prototype_only"] else "evaluated"
        covered = set()
        for rule in ruleset.rules:
            evidence = match(db, checkin, rule)
            if evidence:
                details["matched_rules"].append(rule.id)
                if rule.symptom_code:
                    covered.add(rule.symptom_code)
                guidance = rule.guidance
                if rule.severity == "emergency":
                    guidance += " " + EMERGENCY_GUIDANCE
                persist_alert(db, checkin, rule.id, rule.version, rule.severity, guidance,
                    {"observations": evidence, "rule": rule.model_dump(mode="json"), "ruleset_hash": fingerprint}, rule.prototype_only)
        unassessed = [r["code"] for r in checkin.symptom_reports if r["present"] and r["code"] not in covered]
        if checkin.symptoms or checkin.note or unassessed:
            persist_alert(db, checkin, "unassessed_observations", "1", "needs_clinical_review", FALLBACK_GUIDANCE,
                {"unmatched_codes": unassessed, "free_text_present": bool(checkin.symptoms or checkin.note)})
    evaluation = RiskEvaluation(checkin_id=checkin.id, checkin_version=checkin.version, ruleset_hash=fingerprint, status=status, details=details)
    try:
        with db.begin_nested():
            db.add(evaluation)
            db.flush()
    except IntegrityError:
        evaluation = db.scalar(select(RiskEvaluation).where(RiskEvaluation.checkin_id == checkin.id, RiskEvaluation.ruleset_hash == fingerprint, RiskEvaluation.checkin_version == checkin.version))
    return evaluation


def result(db, checkin):
    evaluation = db.scalar(select(RiskEvaluation).where(RiskEvaluation.checkin_id == checkin.id).order_by(RiskEvaluation.created_at.desc()).limit(1))
    alerts = db.scalars(select(Alert).where(Alert.checkin_id == checkin.id, Alert.patient_id == checkin.patient_id).order_by(Alert.created_at)).all()
    return {"status": evaluation.status if evaluation else "not_evaluated", "prototype_only": evaluation.details["prototype_only"] if evaluation else True,
        "alerts": alerts, "guidance": FALLBACK_GUIDANCE}
