"""Provider boundary. External generators require a separately reviewed adapter."""
from dataclasses import dataclass
from typing import Protocol


class AIUnavailable(Exception):
    pass


@dataclass(frozen=True)
class PatientContext:
    approved_instructions: tuple[str, ...]


class AIProvider(Protocol):
    def respond(self, prompt: str, context: PatientContext, history: list[dict[str, str]]) -> str: ...


class DisabledProvider:
    def respond(self, prompt, context, history):
        raise AIUnavailable("AI provider not configured")


class ApprovedInstructionsProvider:
    """Deterministic integration mode: quotes approved text, never generates advice."""
    def respond(self, prompt, context, history):
        if not context.approved_instructions:
            return "No approved recovery instructions are available. Ask your care team for your instructions. This chat does not diagnose or monitor emergencies."
        return "Approved recovery instructions (quoted, not personalized advice):\n\n" + "\n\n".join(context.approved_instructions)


def build_provider(settings) -> AIProvider:
    if settings.ai_provider == "approved_instructions":
        return ApprovedInstructionsProvider()
    return DisabledProvider()


def respond(provider, prompt, context, history):
    try:
        result = provider.respond(prompt, context, history)
        if not isinstance(result, str) or not result.strip() or len(result) > 20000:
            raise AIUnavailable("Invalid provider response")
        return result
    except Exception as exc:
        # Never expose provider payloads, prompts or credentials in HTTP errors.
        raise AIUnavailable("AI service unavailable") from exc
