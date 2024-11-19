from datetime import datetime, timedelta
from typing import Optional

from app.db import get_session
from app.models import User
from app.settings import Settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


class Token(BaseModel):
    access_token: str
    token_type: str


class DataToken(BaseModel):
    id: Optional[str] = None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
settings = Settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"expire": expire.strftime("%Y-%m-%d %H:%M:%S")})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, ALGORITHM)

    return encoded_jwt


def verify_token_access(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)

        id: str = payload.get("user_id")

        if id is None:
            raise credentials_exception
        token_data = DataToken(id=id)
    except JWTError as e:
        print(e)
        raise credentials_exception

    return token_data


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not Validate Credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = verify_token_access(token, credentials_exception)
    existing_user = await db.execute(select(User).where(User.id == token.id))
    existing_user = existing_user.first()
    return existing_user[0]
