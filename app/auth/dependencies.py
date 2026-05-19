from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt import decode_access_token
from app.models.user import CurrentUser

# This tells FastAPI to look for
# "Authorization: Bearer <token>" in request headers
bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> CurrentUser:
    """
    This function runs on every protected endpoint.
    It reads the JWT token from the request header,
    validates it, and returns the current user.
    If token is missing or invalid, request is rejected
    with 401 error before any logic runs.
    """

    # Extract token from header
    token = credentials.credentials

    try:
        # Decode and validate token
        payload = decode_access_token(token)

        # Extract user info from token
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Return current user object
        return CurrentUser(
            id=user_id,
            email=email,
            full_name=payload.get("full_name", "")
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

# --- Optional Auth ---
# Use this for endpoints that work
# both logged in and logged out

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    )
) -> CurrentUser | None:
    """
    Returns current user if token is present and valid.
    Returns None if no token provided.
    Used for optional authentication.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        return CurrentUser(
            id=payload.get("sub"),
            email=payload.get("email"),
            full_name=payload.get("full_name", "")
        )
    except (ValueError, Exception):
        return None