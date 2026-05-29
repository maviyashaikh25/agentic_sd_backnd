import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from app.utils.db import get_db
from app.models import User
from app.utils.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter()

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    token: str
    user: UserResponse

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    # 1. Clean username
    username_cleaned = user_data.username.strip()
    if not username_cleaned or len(username_cleaned) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters long"
        )
    if len(user_data.password) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 5 characters long"
        )

    # 2. Check if user already exists
    result = await db.execute(select(User).where(User.username == username_cleaned))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken"
        )

    # 3. Create new user
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    hashed_pwd = hash_password(user_data.password)
    
    new_user = User(
        id=user_id,
        username=username_cleaned,
        hashed_password=hashed_pwd
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 4. Generate token
    token = create_token(new_user.id, new_user.username)
    
    return {
        "token": token,
        "user": new_user
    }

@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    username_cleaned = user_data.username.strip()
    
    # 1. Find user
    result = await db.execute(select(User).where(User.username == username_cleaned))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    # 2. Generate token
    token = create_token(user.id, user.username)
    
    return {
        "token": token,
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
