import pytest
from app.modules.policies.rag_service import rag_service
from app.modules.agents.onboarding_agent import onboarding_agent


def test_rag_chunk_markdown_splitting():
    markdown = """# General Leave Policy
This is general guidance for all employees.

## Sick Leave Section
Employees receive 12 days of sick leave per annum with medical certificate requirements for >2 days.

### Mental Health Day
Mental wellness days can be taken once per quarter without doctor certification.

## Remote Work Policy
Remote work is allowed up to 2 days per week upon manager agreement.
"""
    chunks = rag_service.chunk_markdown(markdown, chunk_size=120, chunk_overlap=30)
    assert len(chunks) >= 3

    headers = [c["section_header"] for c in chunks]
    assert any("Sick Leave" in h for h in headers)
    assert any("Remote Work" in h for h in headers)


def test_rag_fallback_vectorizer():
    import numpy as np

    vec1 = np.array(rag_service._local_vectorize("Medical sick leave certificate policy"))
    vec2 = np.array(rag_service._local_vectorize("Sick doctor medical prescription certificate"))
    vec3 = np.array(rag_service._local_vectorize("Stock option equity compensation grant"))

    assert len(vec1) == 512
    sim_1_2 = float(np.dot(vec1, vec2))
    sim_1_3 = float(np.dot(vec1, vec3))
    assert sim_1_2 > sim_1_3


def test_rag_format_grounding_context():
    mock_results = [
        {
            "document_title": "Employee Handbook",
            "section_header": "Maternity Benefits",
            "policy_code": "POL-MAT-01",
            "similarity": 0.88,
            "content": "Female employees are eligible for 26 weeks of paid maternity leave.",
        }
    ]
    context = rag_service.format_rag_grounding_context(mock_results)
    assert "Maternity Benefits" in context
    assert "POL-MAT-01" in context
    assert "26 weeks of paid maternity leave" in context


def test_pypdf_reader_availability():
    import pypdf
    assert hasattr(pypdf, "PdfReader")
    assert hasattr(pypdf, "PdfWriter")


def test_onboarding_agent_email_formatting():
    body = onboarding_agent.format_email_body(
        employee_name="Alice Smith",
        corporate_email="alice.smith@acme.corp",
        initial_password="SecretTempPassword123!",
        company_name="Acme Global",
        personal_email="alice.personal@gmail.com",
        organization_email="hr@acmeglobal.com",
    )
    assert "Alice Smith" in body
    assert "alice.smith@acme.corp" in body
    assert "SecretTempPassword123!" in body
    assert "Acme Global" in body
    assert "alice.personal@gmail.com" in body
    assert "hr@acmeglobal.com" in body
    assert "Direct Email Leave Applications" in body
