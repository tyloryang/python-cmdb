from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token, hash_password
from app.models.user import User, RefreshToken
from app.schemas.user import TokenOut, UserOut
import hashlib

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenOut)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    payload = decode_token(refresh_token)

    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        revoked=False,
        created_at=datetime.now(timezone.utc),
    ))
    await db.execute(
        update(User).where(User.id == user.id).values(last_login=datetime.now(timezone.utc))
    )
    await db.commit()
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenOut)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
    )
    stored = result.scalar_one_or_none()
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌已失效")

    stored.revoked = True
    user_id = int(payload["sub"])
    new_access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    new_payload = decode_token(new_refresh)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=new_hash,
        expires_at=datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc),
        revoked=False,
        created_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return TokenOut(access_token=new_access, refresh_token=new_refresh)


@router.delete("/logout")
async def logout(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    await db.execute(
        update(RefreshToken).where(RefreshToken.token_hash == token_hash).values(revoked=True)
    )
    await db.commit()
    return {"msg": "已退出登录"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
