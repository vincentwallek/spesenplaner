"""
API Gateway — OAuth2/JWT Authentication Module.
Handles user registration, login, token creation/validation, and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, DATABASE_URL


# --- Database Setup ---
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    """User table for authentication."""
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # user, manager, admin
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    full_name: Optional[str] = None
    role: str = Field(default="user", pattern="^(user|manager|admin)$")


class UserResponse(BaseModel):
    username: str
    full_name: Optional[str]
    role: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2 Scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


async def init_db():
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create default admin user if not exists
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.username == "admin"))
        if result.scalar_one_or_none() is None:
            admin = UserDB(
                username="admin",
                hashed_password=pwd_context.hash("admin123"),
                full_name="Administrator",
                role="admin",
            )
            session.add(admin)
            # Create default demo user
            user = UserDB(
                username="demo",
                hashed_password=pwd_context.hash("demo123"),
                full_name="Demo User",
                role="user",
            )
            session.add(user)
            # Create default manager
            manager = UserDB(
                username="manager",
                hashed_password=pwd_context.hash("manager123"),
                full_name="Manager User",
                role="manager",
            )
            session.add(manager)
            await session.commit()


async def get_db() -> AsyncSession:
    """Dependency: Get async database session."""
    async with async_session() as session:
        yield session


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[UserDB]:
    """Authenticate a user by username and password."""
    result = await session.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependency: Extract and validate current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")
        if username is None:
            raise credentials_exception
        return TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception


async def register_user(session: AsyncSession, user_data: UserCreate) -> UserDB:
    """Register a new user."""
    # Check if user already exists
    result = await session.execute(select(UserDB).where(UserDB.username == user_data.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = UserDB(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user


async def get_all_users(session: AsyncSession):
    """Get all registered users."""
    result = await session.execute(select(UserDB).order_by(UserDB.username))
    return list(result.scalars().all())


async def update_user_role(session: AsyncSession, username: str, new_role: str) -> Optional[UserDB]:
    """Update a user's role."""
    result = await session.execute(select(UserDB).where(UserDB.username == username))
    user = result.scalar_one_or_none()
    if user:
        user.role = new_role
        await session.commit()
        await session.refresh(user)
    return user
