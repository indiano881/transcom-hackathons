import datetime
import logging
import sqlite3

import bcrypt
from fastapi import APIRouter, Response
from jose import jwt
from starlette import status

from app import database as db
from app import exception
from app.config import settings
from app.models import RegisterRequest, TokenResponse, LoginRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(req: RegisterRequest):
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    try:
        await db.execute('INSERT INTO user(username,email,password,created_at) VALUES (?,?,?,?)',
                     (req.username, req.email, hashed, datetime.datetime.now(datetime.UTC)),)
    except sqlite3.IntegrityError:
        logger.warning("Failed to insert user", exc_info=True)
        raise exception.ClientIllegalArgumentException('Email already exists')
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    row = await db.fetch_one('SELECT id,email,password FROM user WHERE email=?', (req.email,))
    if not row:
        raise exception.ClientIllegalArgumentException('Invalid email or password')

    user_id, email, password = row
    if not bcrypt.checkpw(req.password.encode(), password.encode()):
        raise exception.ClientIllegalArgumentException('Invalid email or password')

    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret_key, settings.jwt_algorithm)
    return TokenResponse(access_token=token)