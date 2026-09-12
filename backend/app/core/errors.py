from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class DependencyUnavailable(Exception):
    def __init__(self, dependency: str) -> None:
        self.dependency = dependency


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
        headers={"Cache-Control": "no-store"},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def application_error(request: Request, exc: AppError) -> JSONResponse:
        response = error_response(exc.status, exc.code, exc.message)
        if exc.status == 401:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.exception_handler(DependencyUnavailable)
    async def dependency_error(
        request: Request, exc: DependencyUnavailable
    ) -> JSONResponse:
        return error_response(
            503,
            f"{exc.dependency.upper()}_UNAVAILABLE",
            f"The {exc.dependency} dependency is unavailable.",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        messages = {
            "PASSWORD_POLICY_VIOLATION": "Password must contain 10 to 128 characters.",
            "TERMS_NOT_ACCEPTED": "You must accept the Terms of Service.",
            "BULK_KEYWORD_LIMIT_EXCEEDED": (
                "A bulk request may contain at most 1000 keywords."
            ),
            "INVALID_PROJECT_STATUS": "Project status is invalid.",
            "PROJECT_KEYWORD_LIMIT_EXCEEDED": (
                "A Project may contain at most 1000 initial keyword inputs."
            ),
            "INVALID_TRACKED_SITE_STATUS": "Tracked Site status is invalid.",
        }
        for error in exc.errors():
            if error["type"] in messages:
                return error_response(422, error["type"], messages[error["type"]])
        return error_response(422, "VALIDATION_ERROR", "The request is invalid.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        response = error_response(
            exc.status_code,
            "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "Resource not found." if exc.status_code == 404 else "Request failed.",
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response
