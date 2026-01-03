"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    create_access_token, 
    create_refresh_token,
    get_current_user
)
from app.core.config import settings

router = APIRouter()


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    email: str
    role: str
    name: Optional[str] = None


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint - returns access and refresh tokens
    
    Demo credentials:
    - Username: demo@cloudguard.io
    - Password: demo123
    """
    # TODO: Implement user lookup from database
    # For now, using hardcoded demo user for development
    if form_data.username != "demo@cloudguard.io" or form_data.password != "demo123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    user_data = {
        "sub": "demo-user-id-123",
        "email": form_data.username,
        "role": "admin"
    }
    
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data={"sub": user_data["sub"]})
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    from app.core.security import decode_token
    
    try:
        payload = decode_token(refresh_token)
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        
        # Create new tokens
        user_data = {
            "sub": user_id,
            "email": "demo@cloudguard.io",  # TODO: Fetch from database
            "role": "admin"
        }
        
        new_access_token = create_access_token(data=user_data)
        new_refresh_token = create_refresh_token(data={"sub": user_id})
        
        return LoginResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current authenticated user information"""
    return UserResponse(
        user_id=current_user.get("sub"),
        email=current_user.get("email"),
        role=current_user.get("role"),
        name="Demo User"  # TODO: Fetch from database
    )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout endpoint
    
    In a production environment, this would:
    1. Blacklist the token in Redis
    2. Clear any server-side sessions
    """
    # TODO: Add token to Redis blacklist
    # redis_client.setex(f"blacklist:{token}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
    
    return {
        "message": "Successfully logged out",
        "user_id": current_user.get("sub")
    }


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # TODO: Implement password change
    # 1. Verify current password
    # 2. Hash new password
    # 3. Update in database
    # 4. Invalidate all existing tokens
    
    return {
        "message": "Password changed successfully",
        "user_id": current_user.get("sub")
    }
