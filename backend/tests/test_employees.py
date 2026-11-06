from datetime import date
from decimal import Decimal
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.employee import EmployeeCreateRequest, EmployeeUpdateRequest


def test_employee_create_schema_validation():
    req = EmployeeCreateRequest(
        first_name="Alice",
        last_name="Johnson",
        email="alice.johnson@company.com",
        phone="+1234567890",
        designation="Senior Engineer",
        date_of_joining=date(2025, 1, 15),
        salary_basic=Decimal("95000.00"),
    )

    assert req.first_name == "Alice"
    assert req.salary_basic == Decimal("95000.00")
    assert req.employment_type == "full_time"


def test_employee_create_schema_invalid_email():
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(
            first_name="Bob",
            last_name="Smith",
            email="not-an-email",
        )


def test_employee_create_negative_salary_rejected():
    with pytest.raises(ValidationError):
        EmployeeCreateRequest(
            first_name="Bob",
            last_name="Smith",
            email="bob@company.com",
            salary_basic=Decimal("-500.00"),
        )


def test_employee_update_partial():
    update_data = EmployeeUpdateRequest(
        designation="Engineering Lead",
        salary_basic=Decimal("110000.00"),
    )
    dumped = update_data.model_dump(exclude_unset=True)
    assert dumped == {"designation": "Engineering Lead", "salary_basic": Decimal("110000.00")}


@pytest.mark.asyncio
async def test_analyze_import_file_auto_mapping():
    import io
    from fastapi import UploadFile
    from app.modules.employees.service import EmployeeService

    csv_bytes = b"EmployeeID,Name,Department,Experience_Years,Monthly_Salary\n1,Amit,Marketing,15,111416\n2,Sneha,Operations,7,95271\n"
    file = UploadFile(filename="test.csv", file=io.BytesIO(csv_bytes))
    service = EmployeeService(None, uuid.uuid4())
    result = await service.analyze_import_file(file)
    assert result.total_rows == 2
    assert "EmployeeID" in result.detected_columns
    assert result.mapped_fields["EmployeeID"] == "employee_code"
    assert result.mapped_fields["Monthly_Salary"] == "salary_basic"
    assert "Corporate Email (email)" in result.missing_fields
