"""Stable error envelope for vendor backend endpoints.

Wire shape: {"detail": "<human msg>", "code": "<machine code>"}.
Frontend keys off `code`; `detail` is for UI display.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse


class CodedHTTPException(HTTPException):
    """HTTPException 加上 machine-readable `code`，供前端判斷錯誤類型。"""

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


async def _coded_exception_handler(_request: Request, exc: CodedHTTPException) -> JSONResponse:
    # 統一 envelope，避免 FastAPI 預設把 detail 包成 dict 的雙層結構。
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


def install_error_handler(app: FastAPI) -> None:
    """於 FastAPI app 註冊 CodedHTTPException 的 handler。"""
    app.add_exception_handler(CodedHTTPException, _coded_exception_handler)
