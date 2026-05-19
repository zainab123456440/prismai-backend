from fastapi import APIRouter, HTTPException, status, Depends
from passlib.context import CryptContext
from datetime import datetime

from app.models.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.db.supabase import (
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from app.auth.jwt import create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- Password Hashing Setup ---

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash password safely.
    bcrypt supports max 72 bytes,
    so truncate slightly for safety.
    """
    return pwd_context.hash(password[:71])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hashed password.
    """
    return pwd_context.verify(plain_password[:71], hashed_password)


# --- Register ---

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserRegister):
    try:
        # Check if user already exists
        existing_user = get_user_by_email(user_data.email)

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered, Login to Continue"
            )

        # Hash password
        hashed_pw = hash_password(user_data.password)

        # Create user in database
        new_user = create_user(
            email=user_data.email,
            hashed_password=hashed_pw,
            full_name=user_data.full_name,
        )

        # Create JWT token
        token = create_access_token(
            user_id=str(new_user["id"]),
            email=new_user["email"],
        )

        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(new_user["id"]),
                email=new_user["email"],
                full_name=new_user["full_name"],
                created_at=datetime.utcnow(),
            )
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )


# --- Login ---

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    try:
        # Find user
        user = get_user_by_email(user_data.email)

        # Validate credentials
        if not user or not verify_password(
            user_data.password,
            user["password"]
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Create JWT token
        token = create_access_token(
            user_id=str(user["id"]),
            email=user["email"]
        )

        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(user["id"]),
                email=user["email"],
                full_name=user["full_name"],
                created_at=datetime.utcnow(),
            )
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


# --- Current Logged In User ---

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """
    Returns currently authenticated user.
    """

    return {
    "id": str(current_user.id),
    "email": current_user.email,
    "full_name": current_user.full_name,
}