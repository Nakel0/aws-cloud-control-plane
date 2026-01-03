"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token authentication
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a plain password"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Payload data (user_id, email, etc.)
        expires_delta: Optional expiration time override
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token with longer expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user
    
    Usage:
        @app.get("/me")
        def read_current_user(current_user: dict = Depends(get_current_user)):
            return current_user
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    # Verify token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # TODO: Fetch user from database
    # user = db.query(User).filter(User.id == user_id).first()
    # if user is None:
    #     raise HTTPException(status_code=404, detail="User not found")
    
    # For now, return payload
    return payload


def require_role(required_role: str):
    """
    Dependency to require specific role
    
    Usage:
        @app.delete("/resource/{id}")
        def delete_resource(
            id: str,
            current_user: dict = Depends(require_role("admin"))
        ):
            ...
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role")
        
        # Define role hierarchy
        role_hierarchy = {
            "viewer": 1,
            "analyst": 2,
            "admin": 3
        }
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 999):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker
