from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import verify_password, create_access_token
from backend.app.models.user import User
from backend.app.schemas.user import UserResponse, Token, LoginRequest, TokenPayload

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login-form" # standard oauth2 form endpoint
)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency checking JWT token authenticity.
    Returns User DB object or throws 401 Unauthorized status.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenPayload(sub=username)
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == token_data.sub).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


class RoleChecker:
    """
    RBAC Route Inspector.
    Tosses HTTP 403 Forbidden is the currently authenticated user
    does not belong to the permitted role names.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation restricted. Required roles: {self.allowed_roles}. Current role: {current_user.role}"
            )
        return current_user


# Login endpoint (for custom JSON POST requests)
@router.post("/login", response_model=Token)
def login(request_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request_data.username).first()
    if not user or not verify_password(request_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user profile"
        )
        
    # Generate token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user.username, expires_delta=access_token_expires)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }


# Standard OAuth2 form login endpoint (for swagger UI sandbox)
@router.post("/login-form", response_model=Token)
def login_oauth(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=user.username, expires_delta=access_token_expires)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }


# Retrieve Profile details page profile
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# PROTECTED ROUTE TESTS VERIFYING RBACPrivilege Guards
@router.get("/admin-only")
def test_admin_guard(user: User = Depends(RoleChecker(["admin"]))):
    return {"message": "Welcome Admin. Access granted.", "user": user.username}

@router.get("/manager-only")
def test_manager_guard(user: User = Depends(RoleChecker(["admin", "manager"]))):
    return {"message": "Welcome Manager or Admin. Access granted.", "user": user.username}

@router.get("/employee-only")
def test_employee_guard(user: User = Depends(RoleChecker(["admin", "manager", "employee"]))):
    return {"message": "Access granted.", "user": user.username}
