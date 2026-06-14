from app.rules.complaint_rules import classify_complaint_type, judge_severity
from app.schemas.domain import COMPLAINT_TYPES, SEVERITIES, ComplaintCase
from app.services.ai_gateway import AIGateway


class ComplaintService:
    def __init__(self, ai_gateway: AIGateway) -> None:
        self.ai_gateway = ai_gateway

    def analyze(self, text: str) -> ComplaintCase:
        rule_type = classify_complaint_type(text)
        rule_severity = judge_severity(text, rule_type)
        try:
            result = self.ai_gateway.call_structured(
                "complaint_analysis",
                {"text": text, "type": rule_type, "severity": rule_severity},
            )
        except Exception:
            result = {}

        complaint_type = str(result.get("complaint_type", "")).strip()
        if complaint_type not in COMPLAINT_TYPES:
            complaint_type = rule_type

        model_severity = str(result.get("severity", "")).strip()
        severity = self._choose_more_severe(model_severity, judge_severity(text, complaint_type))
        if severity not in SEVERITIES:
            severity = rule_severity

        comfort_reply = str(result.get("comfort_reply", "")).strip() or "非常抱歉给您带来不佳的入住体验，我们会立即记录并协助处理。"
        solution = str(result.get("solution", "")).strip() or "安排工作人员尽快核实并提供现场补救。"
        compensation = str(result.get("compensation", "")).strip() or "可根据现场情况提供合理演示补偿。"
        escalation_note = str(result.get("escalation_note", "")).strip() or "该问题建议上报上级，由管理人员进一步跟进。"
        escalation_summary = str(result.get("escalation_summary", "")).strip() or text[:120]
        if severity == "轻度":
            return ComplaintCase(
                complaint_type=complaint_type,
                severity=severity,
                comfort_reply=comfort_reply,
                solution=solution,
                compensation=compensation,
            )
        return ComplaintCase(
            complaint_type=complaint_type,
            severity=severity,
            comfort_reply=comfort_reply,
            escalation_note=escalation_note,
            escalation_summary=escalation_summary,
        )

    @staticmethod
    def _choose_more_severe(model_severity: str, rule_severity: str) -> str:
        rank = {"轻度": 1, "中度": 2, "重度": 3}
        if model_severity not in rank:
            return rule_severity
        return model_severity if rank[model_severity] >= rank.get(rule_severity, 0) else rule_severity
