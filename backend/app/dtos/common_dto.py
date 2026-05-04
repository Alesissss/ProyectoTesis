"""DTOs genéricos reutilizables."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: bool
    message: str
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T, message: str = "OK") -> "ApiResponse[T]":
        return cls(status=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str) -> "ApiResponse[None]":
        return cls(status=False, message=message, data=None)


class MensajeResponse(BaseModel):
    mensaje: str


class PaginacionParams(BaseModel):
    pagina: int = 1
    por_pagina: int = 20
