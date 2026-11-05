from .schemas import Evaluation, Metrics

WEIGHTS = {
    "correctness": 0.40,
    "test_quality": 0.15,
    "code_quality": 0.15,
    "security": 0.15,
    "efficiency": 0.10,
    "resource_cost": 0.05,
}


def evaluate(metrics: Metrics, *, mandatory_tests_pass: bool, critical_findings: int) -> Evaluation:
    """Score candidates and enforce constraints that weighted scoring cannot override."""
    disqualifiers: list[str] = []
    if not mandatory_tests_pass:
        disqualifiers.append("mandatory functional tests failed")
    if critical_findings:
        disqualifiers.append(f"{critical_findings} confirmed critical security finding(s)")
    score = round(sum(getattr(metrics, key) * weight for key, weight in WEIGHTS.items()), 2)
    return Evaluation(metrics=metrics, score=score, eligible=not disqualifiers, disqualifiers=disqualifiers)
