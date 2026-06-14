from app.rules.complaint_rules import classify_complaint_type, judge_severity
from app.schemas.domain import ComplaintCase
from app.services.ai_gateway import AIGateway


class ComplaintService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def analyze(self, text: str) -> ComplaintCase:
        complaint_type = classify_complaint_type(text)
        severity = judge_severity(text, complaint_type)
        copy = self.ai_gateway.call_structured("complaint_copy", {"text": text, "type": complaint_type, "severity": severity})
        if severity == "轻度":
            return ComplaintCase(
                complaint_type=complaint_type,
                severity=severity,
                comfort_reply=copy["comfort_reply"],
                solution=copy["solution"],
                compensation=copy["compensation"],
            )
        return ComplaintCase(
            complaint_type=complaint_type,
            severity=severity,
            comfort_reply=copy["comfort_reply"],
            escalation_note=copy["escalation_note"],
            escalation_summary=copy["escalation_summary"],
        )
