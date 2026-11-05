from app.schemas import Metrics
from app.scoring import evaluate


def test_critical_security_finding_disqualifies_even_a_high_score():
    metrics = Metrics(correctness=100, test_quality=100, code_quality=100, security=100, efficiency=100, resource_cost=100)
    result = evaluate(metrics, mandatory_tests_pass=True, critical_findings=1)
    assert result.score == 100
    assert not result.eligible
