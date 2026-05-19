from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, status
from app.config import settings


# =========================
# CREATE ACCESS TOKEN
# =========================

def create_access_token(user_id: str, email: str) -> str:
    """
    Create JWT token with user info + expiry.
    """

    expire = datetime.utcnow() + timedelta(
        hours=settings.jwt_expire_hours
    )

    payload = {
        "sub": user_id,                 # user id
        "email": email,                 # user email
        "exp": expire,                  # expiry time
        "iat": datetime.utcnow()       # issued at time
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return token


# =========================
# DECODE ACCESS TOKEN
# =========================

def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT token.
    Raises HTTPException if invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload

    except JWTError:
        # IMPORTANT: do NOT raise ValueError (causes 500 error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )