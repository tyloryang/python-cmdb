from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, get_current_user
from app.models.user import Role, Permission, RolePermission
from app.models.user import User
from app.schemas.user import RoleCreate, RoleOut
from app.schemas.common import PageResult

router = APIRouter(prefix="/roles", tags=["角色管理"])


@router.get("", response_model=PageResult[RoleOut])
async def list_roles(page: int = 1, page_size: int = 20, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    skip = (page - 1) * page_size
    total = await db.scalar(select(func.count()).select_from(Role))
    result = await db.execute(select(Role).offset(skip).limit(page_size))
    return PageResult(total=total, page=page, page_size=page_size, items=list(result.scalars().all()))


@router.post("", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(body: RoleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    role = Role(name=body.name, description=body.description)
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@router.post("/{role_id}/permissions")
async def assign_permission(
    role_id: int,
    resource: str,
    action: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    perm_result = await db.execute(
        select(Permission).where(Permission.resource == resource, Permission.action == action)
    )
    perm = perm_result.scalar_one_or_none()
    if not perm:
        perm = Permission(resource=resource, action=action)
        db.add(perm)
        await db.flush()

    db.add(RolePermission(role_id=role_id, permission_id=perm.id))
    await db.commit()
    return {"msg": f"已为角色 {role.name} 授予 {resource}:{action} 权限"}
