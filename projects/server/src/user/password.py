"""비밀번호 해싱 유틸리티 (bcrypt).

Usage::

    from src.user.password import hash_password, verify_password

    hashed = hash_password("my-secret")
    assert verify_password("my-secret", hashed) is True
"""

import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호가 저장된 bcrypt 해시와 일치하는지 확인한다.

    Args:
        plain_password: 검증할 평문 비밀번호.
        hashed_password: DB에 저장된 bcrypt 해시 문자열.

    Returns:
        일치하면 True.
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱한다.

    Args:
        password: 해싱할 평문 비밀번호.

    Returns:
        bcrypt 해시 문자열.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
