from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.farmer_profile import FarmerProfile
from app.schemas.auth import UserRegister, UserLogin, Token
from app.utils.auth import get_password_hash, verify_password, create_access_token
from app.utils.rate_limiter import rate_limit_login, rate_limit_register

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, dependencies=[Depends(rate_limit_register)])
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user. Public registration always yields a farmer; any client-supplied
    # role is ignored so admin accounts cannot be self-assigned through the API.
    hashed_pw = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_pw,
        role="farmer"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create farmer profile
    profile = FarmerProfile(user_id=user.id)
    db.add(profile)
    db.commit()

    # Generate token
    access_token = create_access_token(data={
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    })

    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        role=user.role
    )


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit_login)])
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token."""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = create_access_token(data={
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    })

    return Token(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        role=user.role
    )


@router.get("/me")
def get_me(db: Session = Depends(get_db),
           current_user: User = Depends(__import__('app.utils.deps', fromlist=['get_current_user']).get_current_user)):
    """Get current user info."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }
