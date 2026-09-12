from fastapi import Response

from app.core.auth_http import clear_refresh_cookie, set_refresh_cookie
from app.core.config import Settings


def test_secure_cookie_flags(settings: Settings) -> None:
    secure = settings.model_copy(
        update={"auth_cookie_secure": True, "auth_cookie_samesite": "strict"}
    )
    response = Response()
    set_refresh_cookie(response, "test-cookie-value", secure)
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
    cleared = Response()
    clear_refresh_cookie(cleared, secure)
    assert "Secure" in cleared.headers["set-cookie"]
    assert "Max-Age=0" in cleared.headers["set-cookie"]
