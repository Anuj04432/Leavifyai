import uuid
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


def test_okf_multi_tenant_company_isolation(tmp_path):
    import shutil
    from app.modules.policies.okf_service import OKFPolicyService

    # Use isolated test directory
    test_svc = OKFPolicyService(knowledge_dir=tmp_path)
    # Ensure templates are available in tmp_path
    for tf in ["annual.md", "casual.md", "sick.md", "unpaid.md"]:
        src = okf_service.templates_dir / tf
        if src.exists():
            shutil.copy(src, test_svc.templates_dir / tf)

    company_a = uuid.uuid4()
    company_b = uuid.uuid4()

    # 1. Both companies start with clean default baseline starter templates
    policies_a = test_svc.list_policies(company_id=company_a)
    policies_b = test_svc.list_policies(company_id=company_b)

    assert len(policies_a) == 4
    assert len(policies_b) == 4

    # 2. Company A uploads a custom proprietary policy
    custom_doc = """# Startup Innovation Days
Employees receive 5 paid days per year for hackathons and research.
"""
    uploaded = test_svc.create_or_upload_policy(
        filename="innovation_policy.md",
        content=custom_doc,
        company_id=company_a,
        metadata={
            "policy_code": "POL-INN-99",
            "title": "Startup Innovation Days",
            "leave_type": "innovation",
            "annual_allowance": 5,
        },
    )
    assert uploaded["policy_code"] == "POL-INN-99"

    # 3. Company A's repository contains the new policy
    codes_a = [p["policy_code"] for p in test_svc.list_policies(company_id=company_a)]
    assert "POL-INN-99" in codes_a

    # 4. Company B's repository is strictly isolated and DOES NOT contain Company A's policy
    codes_b = [p["policy_code"] for p in test_svc.list_policies(company_id=company_b)]
    assert "POL-INN-99" not in codes_b
    assert len(codes_b) == 4

    # 5. Direct code lookup from Company B returns None
    assert test_svc.get_policy_by_code("POL-INN-99", company_id=company_b) is None
    assert test_svc.get_policy_by_code("POL-INN-99", company_id=company_a) is not None
