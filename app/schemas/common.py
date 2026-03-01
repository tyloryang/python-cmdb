from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    items: List[T]


class Resp(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data=None, msg="ok"):
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str, code: int = 1):
        return cls(code=code, msg=msg, data=None)
