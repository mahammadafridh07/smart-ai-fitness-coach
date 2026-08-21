"""
Password hashing utilities.

Uses PBKDF2-HMAC-SHA256 (stdlib `hashlib`) so no extra third-party
dependency is required for Streamlit Cloud deployment.

Stored format: "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>"
"""

import hashlib
import hmac
import os

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with a random salt. Never store plain text."""
    salt = os.urandom(_SALT_BYTES)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )

    return f"{_ALGORITHM}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain-text password against a stored PBKDF2 hash."""
    if not stored_hash:
        return False

    try:
        algorithm, iterations_str, salt_hex, hash_hex = stored_hash.split("$")

        if algorithm != _ALGORITHM:
            return False

        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)

        derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(derived.hex(), hash_hex)

    except (ValueError, AttributeError):
        return False


def is_valid_email(email: str) -> bool:
    """Lightweight email format check (no external dependency needed)."""
    if not email or "@" not in email:
        return False

    local, _, domain = email.partition("@")

    return bool(local) and "." in domain and not domain.startswith(".")
