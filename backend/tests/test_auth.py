from datetime import timedelta
import uuid
import pytest
from app.common.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    raw_password = "SuperSecretPassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_access_token_creation_and_decoding():
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    role = "admin"

    token = create_access_token(
        subject=user_id,
        role=role,
        company_id=company_id,
        employee_id=employee_id,
    )

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == role
    assert payload["company_id"] == str(company_id)
    assert payload["employee_id"] == str(employee_id)
    assert payload["type"] == "access"
    assert "exp" in payload


def test_jwt_refresh_token():
    user_id = uuid.uuid4()
    token = create_refresh_token(subject=user_id)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_invalid_jwt_token_raises_error():
    with pytest.raises(ValueError):
        decode_token("invalid.token.string")
