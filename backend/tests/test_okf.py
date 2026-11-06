import pytest
from app.modules.policies.okf_service import okf_service


def test_okf_service_loads_standard_policies():
    policies = okf_service.list_policies()
    assert len(policies) >= 4

    codes = [p["policy_code"] for p in policies]
    assert "POL-CAS-01" in codes
    assert "POL-SCK-02" in codes
    assert "POL-ANN-03" in codes
    assert "POL-LWP-04" in codes


def test_okf_get_policy_by_type():
    casual = okf_service.get_policy_by_type("casual")
    assert casual is not None
    assert casual["policy_code"] == "POL-CAS-01"
    assert casual["is_paid"] is True
    assert casual["annual_allowance"] == 12

    unpaid = okf_service.get_policy_by_type("unpaid")
    assert unpaid is not None
    assert unpaid["policy_code"] == "POL-LWP-04"
    assert unpaid["is_paid"] is False


def test_okf_format_grounding_context():
    context = okf_service.format_grounding_context("sick")
    assert "POL-SCK-02" in context
    assert "Paid Status: Paid" in context
    assert "Medical & Sick Leave Policy" in context
