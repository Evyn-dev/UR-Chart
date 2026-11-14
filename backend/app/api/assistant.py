"""Voice-assistant safety signal API; does not replace the team's medical-risk engine."""
import re
from fastapi import APIRouter, Depends
from app.auth import current_patient
from app.schemas import Data
from app.schemas.reminders import AssistantTriageRequest, AssistantTriageResult

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Demonstration-only phrase detection: not a validated clinical rule or diagnosis.
_EMERGENCY = (
    r"\b(severe|crushing) chest pain\b",
    r"\b(can(?:not|'t)|unable to) breathe\b",
    r"\bsevere (shortness of breath|difficulty breathing)\b",
    r"\bface droop(?:ing)?\b",
    r"\bslurred speech\b",
    r"\b(unconscious|not breathing)\b",
)
_CONCERN = (
    r"\b(incision|wound) (red|swollen|bleeding|infected)\b",
    r"\b(fever|dizzy|dizziness|palpitations|worsening swelling)\b",
)


def classify(text):
    normalized = text.lower().replace("’", "'")
    if any(re.search(pattern, normalized) for pattern in _EMERGENCY):
        return {
            "category": "emergency",
            "guidance": "Possible emergency. Call local emergency services now (911 in the US). Do not wait for UR Chart.",
            "emergency_mode": True,
        }
    if any(re.search(pattern, normalized) for pattern in _CONCERN):
        return {
            "category": "clinical_followup",
            "guidance": "Contact your surgical care team promptly about your symptoms. If severe or rapidly worsening, call emergency services.",
            "emergency_mode": False,
        }
    return {
        "category": "not_classified",
        "guidance": "No phrase matched this limited demo filter. This does not establish that a symptom is safe.",
        "emergency_mode": False,
    }


@router.post("/triage", response_model=Data[AssistantTriageResult])
def triage(body: AssistantTriageRequest, patient=Depends(current_patient)):
    return {"data": {**classify(body.message), "prototype_only": True}}
