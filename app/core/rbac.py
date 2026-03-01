from functools import wraps
from fastapi import Depends, HTTPException, status
from app.dependencies import get_current_user
from app.models.user import User


def require_permission(resource: str, action: str):
    """RBAC 权限检查装饰器，用于路由依赖注入"""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        for role in current_user.roles:
            for perm in role.permissions:
                if perm.resource == resource and perm.action == action:
                    return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少权限: {resource}:{action}"
        )
    return checker
