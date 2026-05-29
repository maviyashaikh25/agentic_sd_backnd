import os
import hmac
import hashlib
import base64
import time
import uuid
from typing import Optional
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.utils.db import get_db
from app.models import User

# Load secret key or use a default secure key
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "agentdev_secret_key_9f95d820b12ad3f290514fe")

# Default iterations for PBKDF2 password hashing
ITERATIONS = 100000

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16).hex()
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        ITERATIONS
    ).hex()
    return f"{salt}.{ITERATIONS}.{hashed}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its PBKDF2 hash."""
    try:
        parts = hashed_password.split('.')
        if len(parts) != 3:
            return False
        salt, iterations_str, original_hash = parts
        iterations = int(iterations_str)
        
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        ).hex()
        
        return hmac.compare_digest(computed_hash, original_hash)
    except Exception:
        return False

def create_token(user_id: str, username: str, expires_in_days: int = 7) -> str:
    """Create a signed authentication token (expires_in_days default is 7)."""
    # Expiry timestamp in seconds
    expiry = int(time.time()) + (expires_in_days * 24 * 60 * 60)
    
    # Payload format: user_id:username:expiry
    payload = f"{user_id}:{username}:{expiry}"
    payload_b64 = base64.urlsafe_b64encode(payload.encode('utf-8')).decode('utf-8')
    
    # Generate signature using HMAC-SHA256
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        payload_b64.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{payload_b64}.{signature}"

def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a token. Returns payload dict or None if invalid/expired."""
    try:
        parts = token.split('.')
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode('utf-8'),
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            return None
            
        # Decode payload
        decoded_payload = base64.urlsafe_b64decode(payload_b64.encode('utf-8')).decode('utf-8')
        user_id, username, expiry_str = decoded_payload.split(':')
        expiry = int(expiry_str)
        
        # Check expiration
        if time.time() > expiry:
            return None
            
        return {"user_id": user_id, "username": username}
    except Exception:
        return None

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency to extract and authenticate current user via Bearer token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception
        
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    
    if not payload:
        raise credentials_exception
        
    user_id = payload["user_id"]
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise credentials_exception
        
    return user
