from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import StaleDataError


class AppError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "error"):
        self.message, self.status, self.code = message, status, code


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse({"error": e.code, "message": e.message}, status_code=e.status)

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, e: IntegrityError):
        return JSONResponse({"error": "conflict", "message": "البيانات متعارضة مع سجل موجود"}, status_code=409)

    @app.exception_handler(DataError)
    async def _bad_value(_: Request, e: DataError):  # NUL bytes, out-of-range numbers, malformed ids that reach the database
        return JSONResponse({"error": "bad_value", "message": "قيمة غير صالحة في البيانات المدخلة"}, status_code=422)

    @app.exception_handler(StaleDataError)
    async def _stale(_: Request, e: StaleDataError):
        return JSONResponse({"error": "stale", "message": "تم تعديل السجل من مستخدم آخر، أعد تحميل الصفحة"}, status_code=409)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, e: Exception):  # never leak internals
        return JSONResponse({"error": "server_error", "message": "حدث خطأ غير متوقع"}, status_code=500)
